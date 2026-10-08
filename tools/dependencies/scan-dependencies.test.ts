import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, test } from "node:test";
import { fileURLToPath } from "node:url";

import { parse, stringify } from "yaml";

import { scanDependencies } from "./scan-dependencies.ts";

const environment = {
  lockfileVersion: "9.0",
  importers: {
    ".": { packageManagerDependencies: { manager: { version: "fixture" } } },
  },
  packages: { manager: { resolution: { integrity: "fixture-manager" } } },
};
const project = {
  lockfileVersion: "9.0",
  importers: {
    ".": { dependencies: { application: { version: "fixture" } } },
    web: {},
  },
  packages: {
    application: { resolution: { integrity: "fixture-application" } },
  },
};
const multiDocument = `---\n${stringify(environment)}---\n${stringify(project)}`;

type Recorded = {
  args: string[];
  lockfiles: { path: string; contents: string }[];
};

const fixtureDirectories: string[] = [];
after(() => {
  for (const directory of fixtureDirectories)
    rmSync(directory, { recursive: true, force: true });
});

function fixture(contents = multiDocument, status = 0, output = false) {
  const rootDir = mkdtempSync(join(tmpdir(), "dependency-scan-test-"));
  fixtureDirectories.push(rootDir);
  const bin = join(rootDir, "bin");
  mkdirSync(bin);
  const scanner = join(bin, "osv-scanner");
  const recordPath = join(rootDir, "record.json");
  writeFileSync(join(rootDir, "pnpm-lock.yaml"), contents);
  writeFileSync(join(rootDir, "uv.lock"), "version = 1\n");
  writeFileSync(join(rootDir, "osv-scanner.toml"), "# Test config\n");
  writeFileSync(
    scanner,
    `#!/usr/bin/env node
const fs = require("node:fs");
const args = process.argv.slice(2);
const lockfiles = args.flatMap((arg, i) => arg === "--lockfile" ? [{path: args[i + 1], contents: fs.readFileSync(args[i + 1], "utf8")}] : []);
fs.writeFileSync(${JSON.stringify(recordPath)}, JSON.stringify({args, lockfiles}));
${output ? 'process.stdout.write("scanner stdout\\n"); process.stderr.write("scanner stderr\\n");' : ""}
process.exitCode = ${status};
`,
  );
  chmodSync(scanner, 0o755);
  return { rootDir, scanner, recordPath };
}

test("delivers both document graphs, original uv lock and original configuration", () => {
  const input = fixture();
  assert.equal(scanDependencies(input), 0);
  const recorded = JSON.parse(
    readFileSync(input.recordPath, "utf8"),
  ) as Recorded;
  assert.deepEqual(recorded.args.slice(0, 2), ["scan", "source"]);
  assert.equal(recorded.lockfiles.length, 3);
  assert.deepEqual(parse(recorded.lockfiles[0].contents), environment);
  assert.deepEqual(parse(recorded.lockfiles[1].contents), project);
  assert.equal(recorded.lockfiles[2].path, join(input.rootDir, "uv.lock"));
  assert.deepEqual(recorded.args.slice(-2), [
    "--config",
    join(input.rootDir, "osv-scanner.toml"),
  ]);
  assert.equal(existsSync(dirname(recorded.lockfiles[0].path)), false);
  assert.equal(existsSync(dirname(recorded.lockfiles[1].path)), false);
  assert.equal(existsSync(recorded.lockfiles[2].path), true);
  assert.equal(
    readFileSync(join(input.rootDir, "pnpm-lock.yaml"), "utf8"),
    multiDocument,
  );
});

test("supports ordinary single-document project lockfiles", () => {
  const input = fixture(stringify(project));
  assert.equal(scanDependencies(input), 0);
  const recorded = JSON.parse(
    readFileSync(input.recordPath, "utf8"),
  ) as Recorded;
  assert.equal(recorded.lockfiles.length, 2);
  assert.deepEqual(parse(recorded.lockfiles[0].contents), project);
});

test("adds every Cargo lockfile outside hidden, node_modules and target folders", () => {
  const input = fixture();
  for (const folder of [
    "b/src-tauri",
    "a",
    "node_modules/crate",
    "b/src-tauri/target/debug",
    ".git",
  ]) {
    mkdirSync(join(input.rootDir, folder), { recursive: true });
    writeFileSync(join(input.rootDir, folder, "Cargo.lock"), "version = 4\n");
  }
  assert.equal(scanDependencies(input), 0);
  const recorded = JSON.parse(
    readFileSync(input.recordPath, "utf8"),
  ) as Recorded;
  assert.deepEqual(
    recorded.lockfiles.slice(3).map((lockfile) => lockfile.path),
    [
      join(input.rootDir, "a", "Cargo.lock"),
      join(input.rootDir, "b", "src-tauri", "Cargo.lock"),
    ],
  );
});

test("preserves vulnerability and connectivity exit statuses and cleans on failure", () => {
  for (const status of [1, 127]) {
    const input = fixture(multiDocument, status);
    assert.equal(scanDependencies(input), status);
    const recorded = JSON.parse(
      readFileSync(input.recordPath, "utf8"),
    ) as Recorded;
    assert.equal(existsSync(dirname(recorded.lockfiles[0].path)), false);
  }
});

test("refuses parser errors, empty documents and malformed lock mappings before scanning", () => {
  for (const contents of [
    "",
    "---\n",
    "lockfileVersion: [broken\n",
    "lockfileVersion: '9.0'\nlockfileVersion: '9.0'\nimporters: {.: {}}\n",
    "just: text\n",
    "lockfileVersion: '9.0'\nimporters: {}\n",
    "lockfileVersion: '9.0'\nimporters: {.: {}}\npackages: {bad: scalar}\n",
    `${multiDocument}---\n`,
  ]) {
    const input = fixture(contents);
    assert.throws(() => scanDependencies(input), /lockfile|importer|packages/i);
    assert.equal(existsSync(input.recordPath), false);
  }
});

test("CLI preserves the scanner's stdout, stderr and exit status", () => {
  const input = fixture(multiDocument, 127, true);
  const script = fileURLToPath(
    new URL("./scan-dependencies.ts", import.meta.url),
  );
  const result = spawnSync(process.execPath, [script], {
    cwd: input.rootDir,
    env: {
      ...process.env,
      PATH: `${dirname(input.scanner)}:${process.env.PATH ?? ""}`,
    },
    encoding: "utf8",
  });
  assert.equal(result.status, 127);
  assert.equal(result.stdout, "scanner stdout\n");
  assert.equal(result.stderr, "scanner stderr\n");
});
