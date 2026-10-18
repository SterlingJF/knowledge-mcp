#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";

import type { ValidateFunction } from "ajv";
import { Ajv } from "ajv";
import { Ajv2020 } from "ajv/dist/2020.js";
import addFormatsModule from "ajv-formats";
import { parse } from "yaml";

const addFormats = addFormatsModule.default;
const root = resolve(process.argv[2] ?? ".");
const failures: Array<string> = [];
const FIX = "Run `just generate_contract_snapshots`.";
let samples = 0;

for (const suite of findSuites(root)) {
  const folder = dirname(suite);
  const schemas = loadSchemas(folder);
  const listed = listedSchemas(folder);
  for (const expectation of ["pass", "fail"] as const) {
    const dir = join(suite, expectation);
    if (!existsSync(dir)) continue;
    for (const file of readdirSync(dir).filter(isYaml).sort()) {
      samples += 1;
      checkSample(schemas, listed, expectation, join(dir, file));
    }
  }
}

if (samples === 0 && hasSchema(root)) {
  failures.push(`no conformance samples under ${root}`);
}

for (const failure of failures) console.error(failure);
console.log(
  `${samples} samples, ${failures.length} failure${failures.length === 1 ? "" : "s"}`,
);
process.exitCode = failures.length === 0 ? 0 : 1;

interface Listed {
  tool: string;
  validate: ValidateFunction;
}

interface ListedTool {
  name: string;
  outputSchema?: JsonObject;
}

type Json = null | boolean | number | string | Array<Json> | JsonObject;
interface JsonObject {
  [key: string]: Json;
}

// One Ajv instance holds every *.schema.yaml in the folder, so a $ref to a sibling file resolves.
function loadSchemas(folder: string): Ajv2020 {
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  addFormats(ajv);
  for (const file of readdirSync(folder).sort()) {
    if (!file.endsWith(".schema.yaml")) continue;
    const schema = readObject(join(folder, file));
    // Ajv keys a schema by its $id, or by its file name when it has no $id. checkSample looks a
    // schema up by file name.
    ajv.addSchema(schema, typeof schema.$id === "string" ? undefined : file);
  }
  return ajv;
}

// Options copied from @modelcontextprotocol/sdk, validation/ajv-provider.js.
function listedSchemas(folder: string): Map<string, Listed> {
  const found = new Map<string, Listed>();
  const path = join(folder, "tools.json");
  if (!existsSync(path)) return found;
  const ajv = new Ajv({
    strict: false,
    validateFormats: true,
    validateSchema: false,
    allErrors: true,
  });
  addFormats(ajv);
  for (const tool of toolsOf(readJson(path))) {
    const listed = compileListed(ajv, relative(root, path), tool);
    if (listed !== undefined) found.set(listed.id, listed);
  }
  return found;
}

function compileListed(
  ajv: Ajv,
  label: string,
  tool: ListedTool,
): (Listed & { id: string }) | undefined {
  const schema = tool.outputSchema;
  if (schema === undefined) return undefined;
  if (holdsDialect(schema)) {
    failures.push(
      `${label}: the ${tool.name} outputSchema contains a $schema key. Listed output schemas must omit dialect declarations. ${FIX}`,
    );
    return undefined;
  }
  if (schema.type !== "object") {
    failures.push(
      `${label}: the ${tool.name} outputSchema has no type "object" at its root. ${FIX}`,
    );
    return undefined;
  }
  const id = typeof schema.$id === "string" ? schema.$id : "";
  try {
    const validate = ajv.getSchema(id) ?? ajv.compile(schema);
    return { id, tool: tool.name, validate };
  } catch (error) {
    failures.push(
      `${label}: the ${tool.name} outputSchema does not compile with the TypeScript MCP SDK client Ajv options: ${String(error)}`,
    );
    return undefined;
  }
}

function toolsOf(listing: Json): Array<ListedTool> {
  if (!isRecord(listing) || !Array.isArray(listing.tools)) return [];
  const tools: Array<ListedTool> = [];
  for (const tool of listing.tools) {
    if (!isRecord(tool) || typeof tool.name !== "string") continue;
    const schema = tool.outputSchema;
    tools.push(
      isRecord(schema)
        ? { name: tool.name, outputSchema: schema }
        : { name: tool.name },
    );
  }
  return tools;
}

function holdsDialect(node: Json): boolean {
  if (Array.isArray(node)) return node.some(holdsDialect);
  if (!isRecord(node)) return false;
  return Object.entries(node).some(
    ([key, value]) => key === "$schema" || holdsDialect(value),
  );
}

function checkSample(
  ajv: Ajv2020,
  listed: Map<string, Listed>,
  expectation: "pass" | "fail",
  samplePath: string,
): void {
  const name = basename(samplePath).split(".")[0];
  const schemaFile = `${name}.schema.yaml`;
  const label = relative(root, samplePath);
  const schemaPath = join(dirname(dirname(dirname(samplePath))), schemaFile);
  if (!existsSync(schemaPath)) {
    failures.push(`${label}: no schema at ${relative(root, schemaPath)}`);
    return;
  }
  const schemaLabel = relative(root, schemaPath);
  const validate = compiled(ajv, schemaFile, schemaLabel);
  if (validate === undefined) return;
  const sample = readYaml(samplePath);
  const valid = validate(sample);
  if (expectation === "pass" && !valid) {
    failures.push(
      `${label}: the pass sample does not validate against ${schemaLabel}: ${ajv.errorsText(validate.errors)}`,
    );
  }
  if (expectation === "fail" && valid) {
    failures.push(`${label}: the fail sample validates against ${schemaLabel}`);
  }
  const tool = listed.get(schemaFile);
  if (expectation === "pass" && tool !== undefined && !tool.validate(sample)) {
    failures.push(
      `${label}: the pass sample fails the ${tool.tool} outputSchema in tools.json. ${FIX}`,
    );
  }
}

function compiled(
  ajv: Ajv2020,
  schemaFile: string,
  schemaLabel: string,
): ValidateFunction | undefined {
  try {
    const validate = ajv.getSchema(schemaFile);
    if (validate === undefined)
      failures.push(
        `${schemaLabel}: no schema has $id ${schemaFile}. Set $id to the file name.`,
      );
    return validate;
  } catch (error) {
    failures.push(`${schemaLabel} does not compile: ${String(error)}`);
    return undefined;
  }
}

function findSuites(dir: string): Array<string> {
  const suites: Array<string> = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name === "node_modules") continue;
    const path = join(dir, entry.name);
    if (entry.name === "conformance") suites.push(path);
    else suites.push(...findSuites(path));
  }
  return suites;
}

function hasSchema(dir: string): boolean {
  return readdirSync(dir, { withFileTypes: true }).some((entry) =>
    entry.isDirectory()
      ? entry.name !== "node_modules" && hasSchema(join(dir, entry.name))
      : entry.name.endsWith(".schema.yaml"),
  );
}

function isRecord(value: Json | undefined): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readObject(path: string): JsonObject {
  const value = readYaml(path);
  if (!isRecord(value))
    throw new Error(
      `${relative(root, path)}: the top-level value is not a mapping`,
    );
  return value;
}

function readJson(path: string): Json {
  const value: unknown = JSON.parse(readFileSync(path, "utf8"));
  return asJson(value, path);
}

function readYaml(path: string): Json {
  const value: unknown = parse(readFileSync(path, "utf8"));
  return asJson(value, path);
}

function asJson(value: unknown, path: string): Json {
  if (value === null) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value;
  if (Array.isArray(value)) {
    return value.map((item: unknown) => asJson(item, path));
  }
  if (typeof value !== "object") {
    throw new Error(
      `${relative(root, path)}: contains a value that is not JSON`,
    );
  }
  const found: JsonObject = {};
  for (const [key, item] of Object.entries(value)) {
    found[key] = asJson(item, path);
  }
  return found;
}

function isYaml(file: string): boolean {
  return file.endsWith(".yaml") || file.endsWith(".yml");
}
