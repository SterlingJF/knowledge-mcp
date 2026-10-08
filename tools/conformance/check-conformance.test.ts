import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const checker = resolve(
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
  const result = spawnSync(process.execPath, [checker, root], {
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

test("fails when there are no samples at all", () => {
  const root = fixture({ "project/v1/health.schema.yaml": schema });
  const { status, output } = run(root);
  assert.equal(status, 1);
  assert.match(output, /no conformance samples/);
});

test("passes when there are no schemas and no samples", () => {
  const root = fixture({
    "project/v1/vault.rest.openapi.yaml": "---\nopenapi: 3.1.1\n",
  });
  const { status, output } = run(root);
  assert.equal(status, 0, output);
  assert.match(output, /0 samples, 0 failures/);
});
