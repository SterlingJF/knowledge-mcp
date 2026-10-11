import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  statSync,
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

const commit = "v0.10.0";
const longName = `${"a-very-long-folder-name-".repeat(5)}/${"and-a-long-file-name-".repeat(4)}.md`;

const upstream: Record<string, string> = {
  "README.md": "# knowledge-bus\n",
  "protocol/knowledge-bus-protocol.yaml": "protocol: kbp\n",
  "universes/README.md": "# Universes\n",
  "universes/product-development/universe.kbp.yaml": "universe: pd\n",
  "universes/product-development/type-guidance.kbp.yaml": "guidance: pd\n",
  "universes/codebase-recordkeeping/universe.kbp.yaml": "universe: cr\n",
  "universes/a-third-one/universe.kbp.yaml": "universe: third\n",
  "skills/kb-check/SKILL.md": "---\nname: kb-check\n---\n",
  "skills/kb-check/runtime/kbp.py": "print('kbp')\n",
  [`skills/kb-explore/${longName}`]: "long\n",
};

/** A stand-in for GitHub's tarball endpoint: `<dir>/<ref>.tar.gz` with one top folder. */
function source(ref: string, files: Record<string, string> = upstream): string {
  const dir = mkdtempSync(join(tmpdir(), "knowledge-bus-"));
  const top = `knowledge-bus-${ref}`;
  for (const [path, contents] of Object.entries(files)) {
    mkdirSync(dirname(join(dir, "tree", top, path)), { recursive: true });
    writeFileSync(join(dir, "tree", top, path), contents);
  }
  const kbp = join(dir, "tree", top, "skills/kb-check/runtime/kbp.py");
  if (existsSync(kbp)) chmodSync(kbp, 0o755);
  const tar = spawnSync(
    "tar",
    ["-czf", join(dir, `${ref}.tar.gz`), "-C", join(dir, "tree"), top],
    { encoding: "utf8", env: { ...process.env, COPYFILE_DISABLE: "1" } },
  );
  assert.equal(tar.status, 0, tar.stderr);
  return dir;
}

/** A plugin folder whose pyproject.toml pins the knowledge-bus release archive at tag `pin`. */
function plugin(pin: string = commit): string {
  const dir = mkdtempSync(join(tmpdir(), "plugin-"));
  writeFileSync(
    join(dir, "pyproject.toml"),
    `[project]\nname = "knowledge-mcp"\ndependencies = [\n    "knowledge-bus @ https://github.com/SterlingJF/knowledge-bus/releases/download/${pin}/knowledge_bus-0.10.0.tar.gz",\n    "mcp==2.0.0",\n]\n`,
  );
  return dir;
}

function run(dir: string, ...args: string[]) {
  const result = spawnSync(
    process.execPath,
    [script, "--plugin", dir, ...args],
    { encoding: "utf8" },
  );
  return { status: result.status, output: result.stdout + result.stderr };
}

const sha256 = (text: string): string =>
  createHash("sha256").update(text).digest("hex");

test("copies every folder under universes/ and skills/, found by listing, under upstream names", () => {
  const dir = plugin();
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit),
  );
  assert.equal(status, 0, output);
  assert.deepEqual(readdirSync(join(dir, "knowledge-bus/universes")).sort(), [
    "a-third-one",
    "codebase-recordkeeping",
    "product-development",
  ]);
  assert.equal(
    readFileSync(
      join(
        dir,
        "knowledge-bus/universes/product-development/universe.kbp.yaml",
      ),
      "utf8",
    ),
    "universe: pd\n",
  );
  assert.deepEqual(readdirSync(join(dir, "skills")).sort(), [
    "kb-check",
    "kb-explore",
  ]);
  assert.equal(
    readFileSync(join(dir, "skills/kb-explore", longName), "utf8"),
    "long\n",
  );
  assert.equal(
    existsSync(join(dir, "knowledge-bus/universes/README.md")),
    false,
    "a file directly under universes/ is no universe spec folder",
  );
  assert.equal(existsSync(join(dir, "knowledge-bus/protocol")), false);
});

test("keeps the executable bit", () => {
  const dir = plugin();
  run(dir, "--ref", commit, "--source", source(commit));
  const mode = statSync(join(dir, "skills/kb-check/runtime/kbp.py")).mode;
  assert.equal(mode & 0o111, 0o111);
});

test("records the ref, the date and every file's SHA-256 in UPSTREAM.md", () => {
  const dir = plugin();
  run(dir, "--ref", commit, "--source", source(commit));
  const notes = readFileSync(join(dir, "knowledge-bus/UPSTREAM.md"), "utf8");
  assert.match(notes, /^# Upstream\n/);
  assert.match(
    notes,
    new RegExp(`- Ref: \`${commit}\`\\n- Fetched: \\d{4}-\\d{2}-\\d{2}\\n`),
  );
  assert.match(
    notes,
    new RegExp(
      `\\| \`knowledge-bus/universes/product-development/universe\\.kbp\\.yaml\` +\\| \`${sha256("universe: pd\n")}\` +\\|`,
    ),
  );
  assert.match(
    notes,
    new RegExp(
      `\\| \`skills/kb-check/SKILL\\.md\` +\\| \`${sha256("---\nname: kb-check\n---\n")}\``,
    ),
  );
  assert.match(
    notes,
    /\| `universes\/a-third-one\/` +\| `knowledge-bus\/universes\/a-third-one\/` +\|/,
  );
  assert.match(
    notes,
    /\| `skills\/kb-explore\/` +\| `skills\/kb-explore\/` +\|/,
  );
});

test("refuses a git pin: knowledge-bus comes from a release archive", () => {
  const dir = mkdtempSync(join(tmpdir(), "plugin-"));
  writeFileSync(
    join(dir, "pyproject.toml"),
    `[project]\nname = "knowledge-mcp"\ndependencies = [\n    "knowledge-bus @ git+https://github.com/SterlingJF/knowledge-bus@${commit}#subdirectory=checker",\n]\n`,
  );
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit),
  );
  assert.equal(status, 1);
  assert.match(output, /no knowledge-bus pin/);
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});

test("refuses a ref that differs from the knowledge-bus pin and writes nothing", () => {
  const dir = plugin();
  const { status, output } = run(
    dir,
    "--ref",
    "main",
    "--source",
    source("main"),
  );
  assert.equal(status, 1);
  assert.match(output, new RegExp(`main.*${commit}`));
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});

test("refuses when pyproject.toml pins no knowledge-bus release archive", () => {
  const dir = mkdtempSync(join(tmpdir(), "plugin-"));
  writeFileSync(join(dir, "pyproject.toml"), '[project]\nname = "x"\n');
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit),
  );
  assert.equal(status, 1);
  assert.match(output, /no knowledge-bus pin/);
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});

test("writes nothing when the archive is missing", () => {
  const dir = plugin();
  const empty = mkdtempSync(join(tmpdir(), "knowledge-bus-"));
  const { status, output } = run(dir, "--ref", commit, "--source", empty);
  assert.equal(status, 1);
  assert.match(output, new RegExp(`${commit}\\.tar\\.gz`));
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});

test("writes nothing when the archive carries no skills", () => {
  const dir = plugin();
  const files = Object.fromEntries(
    Object.entries(upstream).filter(([path]) => !path.startsWith("skills/")),
  );
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit, files),
  );
  assert.equal(status, 1);
  assert.match(output, /no folders under skills\//);
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});

test("a second refresh drops copies gone upstream and keeps the plugin's own skills", () => {
  const dir = plugin();
  run(dir, "--ref", commit, "--source", source(commit));
  mkdirSync(join(dir, "skills/km-own"), { recursive: true });
  writeFileSync(join(dir, "skills/km-own/SKILL.md"), "own\n");
  const fewer = Object.fromEntries(
    Object.entries(upstream).filter(
      ([path]) =>
        !path.startsWith("universes/a-third-one/") &&
        !path.startsWith("skills/kb-explore/"),
    ),
  );
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit, fewer),
  );
  assert.equal(status, 0, output);
  assert.deepEqual(readdirSync(join(dir, "knowledge-bus/universes")).sort(), [
    "codebase-recordkeeping",
    "product-development",
  ]);
  assert.deepEqual(readdirSync(join(dir, "skills")).sort(), [
    "kb-check",
    "km-own",
  ]);
  assert.doesNotMatch(
    readFileSync(join(dir, "knowledge-bus/UPSTREAM.md"), "utf8"),
    /kb-explore|a-third-one/,
  );
});

test("keeps knowledge-mcp's own km-write skill byte for byte", () => {
  const dir = plugin();
  const own = resolve(
    dirname(script),
    "../../runtime/skills/km-write/SKILL.md",
  );
  mkdirSync(join(dir, "skills/km-write"), { recursive: true });
  writeFileSync(join(dir, "skills/km-write/SKILL.md"), readFileSync(own));
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit),
  );
  assert.equal(status, 0, output);
  assert.deepEqual(
    readFileSync(join(dir, "skills/km-write/SKILL.md")),
    readFileSync(own),
  );
  assert.doesNotMatch(
    readFileSync(join(dir, "knowledge-bus/UPSTREAM.md"), "utf8"),
    /km-write/,
  );
});

test("refuses an upstream skill named km-*, which belongs to knowledge-mcp, and writes nothing", () => {
  const dir = plugin();
  mkdirSync(join(dir, "skills/km-write"), { recursive: true });
  writeFileSync(join(dir, "skills/km-write/SKILL.md"), "own\n");
  const { status, output } = run(
    dir,
    "--ref",
    commit,
    "--source",
    source(commit, {
      ...upstream,
      "skills/km-write/SKILL.md": "---\nname: km-write\n---\n",
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /skills\/km-write\/.*knowledge-mcp/);
  assert.deepEqual(readdirSync(dir).sort(), ["pyproject.toml", "skills"]);
  assert.deepEqual(readdirSync(join(dir, "skills")), ["km-write"]);
  assert.equal(
    readFileSync(join(dir, "skills/km-write/SKILL.md"), "utf8"),
    "own\n",
  );
});

test("refuses a ref that climbs out of the source", () => {
  const { status, output } = run(
    plugin(),
    "--ref",
    "../main",
    "--source",
    source("main"),
  );
  assert.equal(status, 1);
  assert.match(output, /Not a ref: \.\.\/main/);
});

test("fails without a ref", () => {
  const dir = plugin();
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /Usage:/);
  assert.deepEqual(readdirSync(dir), ["pyproject.toml"]);
});
