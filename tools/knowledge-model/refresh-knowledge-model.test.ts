import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "refresh-knowledge-model.ts",
);

const upstream = {
  "protocol/knowledge-bus-protocol.yaml": "protocol: kbp\n",
  "universes/product-development/universe.kbp.yaml": "universe: artifacts\n",
  "universes/product-development/type-guidance.kbp.yaml":
    "guidance: artifacts\n",
};

/** A local stand-in for the repository: `<source>/<ref>/<path>`. */
function source(ref: string, files: Record<string, string> = upstream): string {
  const dir = mkdtempSync(join(tmpdir(), "knowledge-bus-"));
  for (const [path, contents] of Object.entries(files)) {
    mkdirSync(dirname(join(dir, ref, path)), { recursive: true });
    writeFileSync(join(dir, ref, path), contents);
  }
  return dir;
}

function run(...args: string[]) {
  const dest = mkdtempSync(join(tmpdir(), "upstream-"));
  const result = spawnSync(
    process.execPath,
    [script, "--dest", dest, ...args],
    { encoding: "utf8" },
  );
  return { dest, status: result.status, output: result.stdout + result.stderr };
}

const sha256 = (text: string): string =>
  createHash("sha256").update(text).digest("hex");

test("copies the three files under their local names", () => {
  const { dest, status, output } = run("--ref", "v2", "--source", source("v2"));
  assert.equal(status, 0, output);
  assert.equal(
    readFileSync(join(dest, "Knowledge Bus Protocol (KBP).yaml"), "utf8"),
    "protocol: kbp\n",
  );
  assert.equal(
    readFileSync(join(dest, "Artifact Universe.kbp.yaml"), "utf8"),
    "universe: artifacts\n",
  );
  assert.equal(
    readFileSync(
      join(dest, "Artifact Universe.type-guidance.kbp.yaml"),
      "utf8",
    ),
    "guidance: artifacts\n",
  );
});

test("writes UPSTREAM.md with the ref, the date, each upstream path and each hash", () => {
  const { dest } = run("--ref", "main", "--source", source("main"));
  const notes = readFileSync(join(dest, "UPSTREAM.md"), "utf8");
  assert.match(notes, /^# Upstream\n/);
  assert.match(notes, /\| File +\| Path when vendored +\|/);
  assert.match(notes, /- Ref: `main`\n- Fetched: \d{4}-\d{2}-\d{2}\n/);
  assert.match(
    notes,
    /\| `Knowledge Bus Protocol \(KBP\)\.yaml` +\| `protocol\/knowledge-bus-protocol\.yaml` +\|/,
  );
  assert.match(
    notes,
    new RegExp(
      `\\| \`Artifact Universe\\.kbp\\.yaml\` +\\| \`${sha256("universe: artifacts\n")}\``,
    ),
  );
  assert.match(notes, new RegExp(sha256("guidance: artifacts\n")));
});

test("writes nothing when a file is missing at the ref", () => {
  const { dest, status, output } = run(
    "--ref",
    "old",
    "--source",
    source("old", {
      "spec/knowledge-bus-protocol.yaml": "protocol: kbp\n",
      "universes/product-development/universe.kbp.yaml": "universe: x\n",
      "universes/product-development/type-guidance.kbp.yaml": "guidance: x\n",
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /protocol\/knowledge-bus-protocol\.yaml/);
  assert.deepEqual(readdirSync(dest), []);
});

test("refuses a ref that climbs out of the source", () => {
  const { status, output } = run(
    "--ref",
    "../main",
    "--source",
    source("main"),
  );
  assert.equal(status, 1);
  assert.match(output, /Not a ref: \.\.\/main/);
});

test("fails without a ref", () => {
  const { dest, status, output } = run();
  assert.equal(status, 1);
  assert.match(output, /Usage:/);
  assert.equal(existsSync(join(dest, "UPSTREAM.md")), false);
});
