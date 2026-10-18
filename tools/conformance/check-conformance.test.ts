import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "check-conformance.ts",
);

const schema = `---
$schema: https://json-schema.org/draft/2020-12/schema
type: object
required: [status]
additionalProperties: false
properties:
  status:
    const: healthy
`;

function fixture(files: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "contracts-"));
  for (const [path, contents] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), contents);
  }
  return root;
}

function run(root: string) {
  const result = spawnSync(process.execPath, [script, root], {
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("passes when pass samples validate and fail samples do not", () => {
  const root = fixture({
    "project/v1/health.schema.yaml": schema,
    "project/v1/conformance/pass/health.ok.yaml": "---\nstatus: healthy\n",
    "project/v1/conformance/fail/health.empty.yaml": "--- {}\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 0, output);
  assert.match(output, /2 samples/);
});

test("fails when a pass sample does not validate", () => {
  const root = fixture({
    "project/v1/health.schema.yaml": schema,
    "project/v1/conformance/pass/health.wrong.yaml": "---\nstatus: down\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 1);
  assert.match(output, /health\.wrong\.yaml/);
});

test("fails when a fail sample validates", () => {
  const root = fixture({
    "project/v1/health.schema.yaml": schema,
    "project/v1/conformance/fail/health.ok.yaml": "---\nstatus: healthy\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 1);
  assert.match(output, /health\.ok\.yaml/);
});

test("fails when a sample has no matching schema", () => {
  const root = fixture({
    "project/v1/conformance/pass/missing.ok.yaml": "---\nstatus: healthy\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 1);
  assert.match(output, /missing\.schema\.yaml/);
});

test("finds conformance suites under plugins and extensions", () => {
  const root = fixture({
    "plugins/tracker/v1/item.schema.yaml": schema,
    "plugins/tracker/v1/conformance/pass/item.ok.yaml":
      "---\nstatus: healthy\n",
    "extensions/host/v1/item.schema.yaml": schema,
    "extensions/host/v1/conformance/fail/item.empty.yaml": "--- {}\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 0, output);
  assert.match(output, /2 samples/);
});

test("fails when the tree has schemas but no samples", () => {
  const root = fixture({ "project/v1/health.schema.yaml": schema });
  const { status, output } = run(root);
  assert.equal(status, 1);
  assert.match(output, /no conformance samples/);
});

test("passes when there are no schemas and no samples", () => {
  const root = fixture({
    "project/v1/health.rest.openapi.yaml": "---\nopenapi: 3.1.1\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 0, output);
  assert.match(output, /0 samples, 0 failures/);
});

const common = `---
$schema: https://json-schema.org/draft/2020-12/schema
$id: common.schema.yaml
$defs:
  status:
    type: string
    const: healthy
`;

const health = `---
$schema: https://json-schema.org/draft/2020-12/schema
$id: health.schema.yaml
type: object
required: [status]
additionalProperties: false
properties:
  status:
    $ref: common.schema.yaml#/$defs/status
`;

const listedHealth = {
  $id: "health.schema.yaml",
  type: "object",
  required: ["status"],
  additionalProperties: false,
  properties: { status: { type: "string", const: "healthy" } },
};

function toolsJson(...outputSchemas: Array<[string, unknown]>): string {
  const tools = outputSchemas.map(([name, outputSchema]) => ({
    name,
    inputSchema: { type: "object", additionalProperties: false },
    outputSchema,
  }));
  return `${JSON.stringify({ tools }, null, 2)}\n`;
}

// Avoid $ref resolution errors so these tests isolate tools.json validation.
const standalone = `---
$schema: https://json-schema.org/draft/2020-12/schema
$id: health.schema.yaml
type: object
required: [status]
additionalProperties: false
properties:
  status:
    type: string
    const: healthy
`;

function suite(tools: string) {
  return {
    "extensions/mcp/v1/health.schema.yaml": standalone,
    "extensions/mcp/v1/conformance/pass/health.ok.yaml":
      "---\nstatus: healthy\n",
    "extensions/mcp/v1/tools.json": tools,
  };
}

test("resolves a $ref to another schema in the same version folder", () => {
  const root = fixture({
    "extensions/mcp/v1/common.schema.yaml": common,
    "extensions/mcp/v1/health.schema.yaml": health,
    "extensions/mcp/v1/conformance/pass/health.ok.yaml":
      "---\nstatus: healthy\n",
    "extensions/mcp/v1/conformance/fail/health.down.yaml":
      "---\nstatus: down\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 0, output);
  assert.match(output, /2 samples, 0 failures/);
});

test("fails when a tools.json outputSchema does not compile with the Ajv options of the TypeScript MCP SDK", () => {
  const listed = run(fixture(suite(toolsJson(["kb_health", listedHealth]))));
  assert.equal(listed.status, 0, listed.output);

  const broken = {
    type: "object",
    properties: { status: { type: "string", pattern: "([" } },
  };
  const { status, output } = run(
    fixture(
      suite(toolsJson(["kb_health", listedHealth], ["kb_broken", broken])),
    ),
  );
  assert.equal(status, 1, output);
  assert.match(output, /kb_broken/);
  assert.doesNotMatch(output, /kb_health/);
});

test("fails when a tools.json outputSchema contains $schema or has no object root", () => {
  const dialect = {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    ...listedHealth,
  };
  const withDialect = run(fixture(suite(toolsJson(["kb_dialect", dialect]))));
  assert.equal(withDialect.status, 1, withDialect.output);
  assert.match(withDialect.output, /kb_dialect/);
  assert.match(withDialect.output, /\$schema/);

  const noRoot = { oneOf: [listedHealth, { type: "object" }] };
  const withoutRoot = run(fixture(suite(toolsJson(["kb_rootless", noRoot]))));
  assert.equal(withoutRoot.status, 1, withoutRoot.output);
  assert.match(withoutRoot.output, /kb_rootless/);
});

test("fails when a pass sample breaks the tools.json outputSchema with the same $id", () => {
  const stricter = {
    ...listedHealth,
    properties: { status: { type: "string", const: "down" } },
  };
  const { status, output } = run(
    fixture(suite(toolsJson(["kb_health", stricter]))),
  );
  assert.equal(status, 1, output);
  assert.match(output, /health\.ok\.yaml/);
  assert.match(output, /kb_health/);
});
