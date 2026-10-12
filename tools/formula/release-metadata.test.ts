import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";

import { check, resolveConfig } from "prettier";

import { prepare, releaseNotes, validateMetadata } from "./release-metadata.ts";
import type { Run } from "./release-metadata.ts";

const projectRoot = resolve(import.meta.dirname, "../..");
const files = [
  "runtime/pyproject.toml",
  "package.json",
  "runtime/.claude-plugin/plugin.json",
  "runtime/.codex-plugin/plugin.json",
  "uv.lock",
  "runtime/requirements.lock",
  "pnpm-lock.yaml",
  "CHANGELOG.md",
];
function fixture(context: TestContext) {
  const root = mkdtempSync(join(tmpdir(), "release metadata "));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  for (const name of files.filter((file) => file !== "CHANGELOG.md")) {
    const target = join(root, name);
    mkdirSync(resolve(target, ".."), { recursive: true });
    copyFileSync(join(projectRoot, name), target);
    if (name.endsWith(".json")) {
      const value = JSON.parse(readFileSync(target, "utf8"));
      value.version = "0.2.0";
      writeFileSync(target, JSON.stringify(value, null, 2) + "\n");
    }
  }
  const manifest = join(root, "runtime/pyproject.toml");
  writeFileSync(
    manifest,
    readFileSync(manifest, "utf8").replace(
      /^version = "[^"]+"/m,
      'version = "0.2.0"',
    ),
  );
  const lock = join(root, "uv.lock");
  writeFileSync(
    lock,
    readFileSync(lock, "utf8").replace(
      /(\[\[package\]\]\nname = "knowledge-mcp"\nversion = ")[^"]+/,
      "$10.2.0",
    ),
  );
  writeFileSync(
    join(root, "CHANGELOG.md"),
    "# Changelog\n\n## 0.2.1 — unreleased\n\n- Improve CLI diagnostics.\n\n## 0.2.0\n\n- Keep source installation.\n",
  );
  writeFileSync(join(root, "README.md"), "User working copy.\n");
  return root;
}
function bytes(root: string) {
  return files.map((file) => readFileSync(join(root, file)));
}
function successfulRun(root: string, calls: Array<string>): Run {
  return (command, args) => {
    calls.push([command, ...args].join(" "));
    if (command === "git") return "";
    if (command === "uv") {
      const lock = join(root, "uv.lock");
      writeFileSync(
        lock,
        readFileSync(lock, "utf8").replace(
          /(\[\[package\]\]\nname = "knowledge-mcp"\nversion = ")[^"]+/,
          "$10.2.1",
        ),
      );
      return "";
    }
    assert.deepEqual(
      [command, ...args],
      ["just", "generate_knowledge_mcp_lock"],
    );
    return "";
  };
}

test("prepare promotes the matching draft, synchronizes shipped versions and preserves unrelated work and pins", async (context) => {
  const root = fixture(context);
  const requirements = readFileSync(join(root, "runtime/requirements.lock"));
  const readme = readFileSync(join(root, "README.md"));
  const pnpmLock = readFileSync(join(root, "pnpm-lock.yaml"));
  const calls: Array<string> = [];
  await prepare(root, "0.2.1", successfulRun(root, calls));
  assert.equal(validateMetadata(root), "0.2.1");
  assert.equal(releaseNotes(root, "0.2.1"), "- Improve CLI diagnostics.");
  for (const path of files.filter((file) => file.endsWith(".json")))
    assert.equal(
      JSON.parse(readFileSync(join(root, path), "utf8")).version,
      "0.2.1",
    );
  assert.deepEqual(readFileSync(join(root, "README.md")), readme);
  assert.deepEqual(
    readFileSync(join(root, "runtime/requirements.lock")),
    requirements,
  );
  assert.deepEqual(readFileSync(join(root, "pnpm-lock.yaml")), pnpmLock);
  assert.ok(calls.includes("uv lock --offline"));
  assert.ok(calls.includes("just generate_knowledge_mcp_lock"));
  assert.ok(
    calls.every(
      (call) =>
        !call.includes("push") &&
        !call.includes("commit") &&
        !call.includes(" add ") &&
        !call.startsWith("gh "),
    ),
  );
});

test("prepared JSON follows the project formatter for each metadata path", async (context) => {
  const root = fixture(context);
  const packagePath = join(root, "package.json");
  writeFileSync(
    packagePath,
    readFileSync(packagePath, "utf8").replace(
      /"engines":\s*\{\s*"node":\s*"([^"]*)"\s*\}/,
      '"engines": { "node": "$1" }',
    ),
  );
  await prepare(root, "0.2.1", successfulRun(root, []));
  for (const file of files.filter((name) => name.endsWith(".json"))) {
    const filepath = join(projectRoot, file);
    assert.equal(
      await check(readFileSync(join(root, file), "utf8"), {
        ...(await resolveConfig(filepath)),
        filepath,
      }),
      true,
      `${file} must pass the normal project formatter`,
    );
  }
});

for (const heading of [
  "## 0.2.1 (unreleased)",
  "## 0.2.1 - UNRELEASED",
  "## Unreleased",
])
  test(`prepare supports ${heading}`, async (context) => {
    const root = fixture(context);
    const path = join(root, "CHANGELOG.md");
    writeFileSync(
      path,
      readFileSync(path, "utf8").replace("## 0.2.1 — unreleased", heading),
    );
    await prepare(root, "0.2.1", successfulRun(root, []));
    assert.equal(releaseNotes(root, "0.2.1"), "- Improve CLI diagnostics.");
  });

for (const version of [
  "v0.2.1",
  "0.2",
  "00.2.1",
  "0.2.1-rc1",
  "0.2.0",
  "0.1.9",
])
  test(`invalid/non-increasing ${version} changes no bytes`, async (context) => {
    const root = fixture(context),
      before = bytes(root);
    await assert.rejects(prepare(root, version, successfulRun(root, [])));
    assert.deepEqual(bytes(root), before);
  });

test("existing tags and ambiguous drafts are rejected before metadata mutation", async (context) => {
  const root = fixture(context),
    before = bytes(root);
  await assert.rejects(
    prepare(root, "0.2.1", () => "v0.2.1"),
    /already exists/,
  );
  assert.deepEqual(bytes(root), before);
  const path = join(root, "CHANGELOG.md");
  writeFileSync(
    path,
    readFileSync(path, "utf8") + "\n## 0.2.1 (unreleased)\n\n- Duplicate.\n",
  );
  const duplicated = bytes(root);
  await assert.rejects(
    prepare(root, "0.2.1", successfulRun(root, [])),
    /duplicate|one|multiple/i,
  );
  assert.deepEqual(bytes(root), duplicated);
});

test("missing draft scaffolds notes while release validation stops on the placeholder", async (context) => {
  const root = fixture(context);
  writeFileSync(
    join(root, "CHANGELOG.md"),
    "# Changelog\n\n## 0.2.0\n\n- Original.\n",
  );
  await prepare(root, "0.2.1", successfulRun(root, []));
  assert.equal(validateMetadata(root), "0.2.1");
  assert.throws(() => releaseNotes(root, "0.2.1"), /TODO|Finish|placeholder/i);
});

for (const notes of [
  "## 0.2.0 (unreleased)\n\n- Draft.",
  "## 0.2.0\n",
  "## 0.2.0\n\n- TODO: Fill notes.",
  "## 0.2.0\n\n- TBD.",
  "## 0.3.0\n\n- Wrong version.",
  "## 0.2.0\n\n- One.\n\n## 0.2.0\n\n- Two.",
])
  test(`incomplete release notes rejected: ${notes.split("\n")[0]}`, (context) => {
    const root = fixture(context);
    writeFileSync(join(root, "CHANGELOG.md"), "# Changelog\n\n" + notes + "\n");
    assert.throws(() => releaseNotes(root, "0.2.0"));
  });

for (const path of [
  "package.json",
  "runtime/.claude-plugin/plugin.json",
  "runtime/.codex-plugin/plugin.json",
  "uv.lock",
])
  test(`metadata rejects mismatched ${path}`, (context) => {
    const root = fixture(context),
      target = join(root, path);
    writeFileSync(
      target,
      readFileSync(target, "utf8").replace('"0.2.0"', '"0.3.0"'),
    );
    assert.throws(() => validateMetadata(root), /version|differs|match/i);
  });

test("failed lock refresh restores metadata, notes, and partly written lock bytes", async (context) => {
  const root = fixture(context),
    before = bytes(root);
  const run: Run = (command) => {
    if (command === "git") return "";
    writeFileSync(join(root, "uv.lock"), "partial lock\n");
    writeFileSync(
      join(root, "runtime/requirements.lock"),
      "partial requirements\n",
    );
    throw new Error("lock refresh failed");
  };
  await assert.rejects(prepare(root, "0.2.1", run), /lock refresh failed/);
  assert.deepEqual(bytes(root), before);
});

test("unrelated dependency changes abort and roll back the whole preparation", async (context) => {
  const root = fixture(context),
    before = bytes(root),
    good = successfulRun(root, []);
  await assert.rejects(
    prepare(root, "0.2.1", (command, args, options) => {
      const result = good(command, args, options);
      if (command === "uv") {
        const lock = join(root, "uv.lock");
        writeFileSync(
          lock,
          readFileSync(lock, "utf8").replace(
            'name = "knowledge-bus"\nversion = "0.10.0"',
            'name = "knowledge-bus"\nversion = "0.11.0"',
          ),
        );
      }
      return result;
    }),
    /dependencies|pins|lock/i,
  );
  assert.deepEqual(bytes(root), before);
});

test("root release recipes share preparation and the native lock-check authority", async () => {
  const { spawnSync } = await import("node:child_process");
  const prepared = spawnSync(
    "just",
    ["--dry-run", "release_prepare", "0.2.1"],
    { cwd: projectRoot, encoding: "utf8" },
  );
  assert.equal(prepared.status, 0, prepared.stderr);
  assert.match(
    prepared.stdout + prepared.stderr,
    /release-metadata\.ts prepare --version '0\.2\.1'/,
  );
  const checked = spawnSync("just", ["--dry-run", "release_check"], {
    cwd: projectRoot,
    encoding: "utf8",
  });
  assert.equal(checked.status, 0, checked.stderr);
  assert.match(checked.stdout + checked.stderr, /uv export .*--locked/);
  assert.match(checked.stdout + checked.stderr, /release-metadata\.ts check/);
});

for (const forced of [
  { FORCE_COLOR: "1" },
  { CLICOLOR_FORCE: "1" },
  { FORCE_COLOR: "1", CLICOLOR_FORCE: "1", UV_COLOR: "always" },
]) {
  test(`requirements generation and checking stay plain under ${Object.keys(forced).join(" + ")}`, (context) => {
    const root = fixture(context);
    copyFileSync(
      join(projectRoot, "pyproject.toml"),
      join(root, "pyproject.toml"),
    );
    const path = join(root, "runtime/requirements.lock");
    const baseline = readFileSync(path);
    const env = {
      ...process.env,
      ...forced,
      NO_COLOR: "",
      UV_OFFLINE: "1",
      UV_PYTHON_DOWNLOADS: "never",
    };
    const run = (recipe: string, args: Array<string> = []) =>
      execFileSync(
        "just",
        [
          "--justfile",
          join(projectRoot, "justfile"),
          "--working-directory",
          root,
          recipe,
          ...args,
        ],
        { cwd: root, env, stdio: ["ignore", "pipe", "pipe"] },
      );
    run("generate_knowledge_mcp_lock");
    const generated = readFileSync(path);
    assert.equal(
      generated.includes(0x1b),
      false,
      "requirements must contain no terminal escapes",
    );
    assert.deepEqual(generated, baseline);
    run("check_knowledge_mcp_lock", [root]);
    writeFileSync(
      path,
      Buffer.concat([baseline, Buffer.from("# stale lock fixture\n")]),
    );
    assert.throws(
      () => run("check_knowledge_mcp_lock", [root]),
      /requirements.lock is stale/,
    );
  });
}

test("preparation delegates to a plain native requirements export under forced color", async (context) => {
  const root = fixture(context);
  copyFileSync(
    join(projectRoot, "pyproject.toml"),
    join(root, "pyproject.toml"),
  );
  const baseline = readFileSync(join(root, "runtime/requirements.lock"));
  const env = {
    ...process.env,
    FORCE_COLOR: "1",
    CLICOLOR_FORCE: "1",
    UV_COLOR: "always",
    NO_COLOR: "",
    UV_OFFLINE: "1",
    UV_PYTHON_DOWNLOADS: "never",
  };
  const run: Run = (command, args, options) => {
    if (command === "git") return "";
    const nativeArgs =
      command === "just"
        ? [
            "--justfile",
            join(projectRoot, "justfile"),
            "--working-directory",
            root,
            ...args,
          ]
        : args;
    return execFileSync(command, nativeArgs, {
      cwd: options?.cwd,
      env,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  };
  await prepare(root, "0.2.1", run);
  assert.deepEqual(
    readFileSync(join(root, "runtime/requirements.lock")),
    baseline,
  );
  assert.equal(validateMetadata(root), "0.2.1");
});
