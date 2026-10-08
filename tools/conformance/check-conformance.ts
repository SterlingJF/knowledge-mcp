#!/usr/bin/env node

// Checks every conformance/{pass,fail} sample against <name>.schema.yaml in its version folder.
// A contracts folder with no *.schema.yaml files has nothing to check and passes.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename, dirname, join, relative, resolve } from "node:path";

import { Ajv2020 } from "ajv/dist/2020.js";
import addFormatsModule from "ajv-formats";
import { parse } from "yaml";

const addFormats = addFormatsModule.default;
const root = resolve(process.argv[2] ?? ".");
const failures: string[] = [];
let samples = 0;

for (const suite of findSuites(root)) {
  for (const expectation of ["pass", "fail"] as const) {
    const dir = join(suite, expectation);
    if (!existsSync(dir)) continue;
    for (const file of readdirSync(dir).filter(isYaml).sort()) {
      samples += 1;
      checkSample(suite, expectation, join(dir, file));
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

function checkSample(
  suite: string,
  expectation: "pass" | "fail",
  samplePath: string,
): void {
  const name = basename(samplePath).split(".")[0];
  const schemaPath = join(dirname(suite), `${name}.schema.yaml`);
  const label = relative(root, samplePath);
  if (!existsSync(schemaPath)) {
    failures.push(`${label}: no schema at ${relative(root, schemaPath)}`);
    return;
  }
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  addFormats(ajv);
  const validate = ajv.compile(readYaml(schemaPath) as object);
  const valid = validate(readYaml(samplePath));
  if (expectation === "pass" && !valid) {
    failures.push(
      `${label}: expected valid, ${ajv.errorsText(validate.errors)}`,
    );
  }
  if (expectation === "fail" && valid) {
    failures.push(`${label}: expected invalid, but it validates`);
  }
}

function findSuites(dir: string): string[] {
  const suites: string[] = [];
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

function readYaml(path: string): unknown {
  return parse(readFileSync(path, "utf8"));
}

function isYaml(file: string): boolean {
  return file.endsWith(".yaml") || file.endsWith(".yml");
}
