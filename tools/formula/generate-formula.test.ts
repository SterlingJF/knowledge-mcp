import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { evaluate, generate, requirementsFor } from "./generate-formula.ts";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const script = join(here, "generate-formula.ts");
const lock = readFileSync(join(root, "uv.lock"), "utf8");
const requirements = readFileSync(
  join(root, "runtime/requirements.lock"),
  "utf8",
);
const pyproject = readFileSync(join(root, "runtime/pyproject.toml"), "utf8");
const version = /^version = "([^"]+)"/m.exec(pyproject)![1];
const sdist = Buffer.from("a stand-in for the release's source archive\n");

function formula(): string {
  return generate({ sdist, lock, requirements, pyproject });
}

function run(...args: Array<string>) {
  const result = spawnSync(process.execPath, [script, ...args], {
    cwd: root,
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("the formula installs knowledge-mcp from its release archive", () => {
  const text = formula();
  assert.match(
    text,
    new RegExp(
      `url "https://github.com/SterlingJF/knowledge-mcp/releases/download/v${version}/knowledge_mcp-${version}.tar.gz"`,
    ),
  );
  assert.match(
    text,
    new RegExp(`sha256 "${createHash("sha256").update(sdist).digest("hex")}"`),
  );
  assert.match(text, /depends_on "python@3\.14"/);
  assert.match(text, /license "MIT"/);
});

test("knowledge-bus comes from its release archive with the hash uv.lock holds", () => {
  const block =
    /resource "knowledge-bus" do\n {4}url "([^"]+)"\n {4}sha256 "([0-9a-f]{64})"\n {2}end/.exec(
      formula(),
    );
  assert.ok(block);
  assert.equal(
    block[1],
    "https://github.com/SterlingJF/knowledge-bus/releases/download/v0.10.0/knowledge_bus-0.10.0.tar.gz",
  );
  assert.match(lock, new RegExp(`hash = "sha256:${block[2]}"`));
});

test("every macOS requirement becomes a source resource; other platforms' stay out", () => {
  const text = formula();
  const names = [...text.matchAll(/resource "([^"]+)" do/g)].map((m) => m[1]);
  const wanted = requirementsFor(requirements).map((r) => r.name);
  assert.deepEqual([...names].sort(), [...wanted].sort());
  for (const name of ["mcp", "pydantic-core", "pyyaml", "cryptography"]) {
    assert.ok(names.includes(name), name);
  }
  for (const name of ["colorama", "pywin32", "httpx2-jsfetch"]) {
    assert.ok(!names.includes(name), name);
  }
  for (const match of text.matchAll(/^ {4}url "([^"]+)"$/gm)) {
    assert.match(match[1], /\.tar\.gz$|\.zip$/);
  }
});

test("native builds get their tools and libraries", () => {
  const text = formula();
  assert.match(text, /depends_on "rust" => :build/);
  assert.match(text, /depends_on "openssl@3"/);
  const order = [...text.matchAll(/^ {2}depends_on "([^"]+)"( => :build)?$/gm)];
  const firstRuntime = order.findIndex((m) => !m[2]);
  assert.ok(order.slice(firstRuntime).every((m) => !m[2]));
});

test("the test block runs kb, kbp through kb, and an MCP initialize over stdio", () => {
  const text = formula();
  assert.match(text, /shell_output\("#\{bin\}\/kb --version"\)/);
  assert.match(text, /shell_output\("#\{bin\}\/kb kbp --version"\)/);
  assert.match(
    text,
    /pipe_output\("#\{bin\}\/kb mcp", "#\{JSON\.generate\(initialize\)\}\\n", 0\)/,
  );
  assert.match(text, /KNOWLEDGE_MCP_DATA: +opt_libexec\/site_packages/);
  // Homebrew style allows longer lines only for URLs.
  for (const line of text.split("\n")) {
    if (!/^ +url "/.test(line)) assert.ok(line.length <= 118, line);
  }
});

test("the caveats name the variable and the history folder it points to", () => {
  const caveats = /^ {2}def caveats\n([\s\S]*?)\n {2}end$/m.exec(formula());
  assert.ok(caveats);
  const text = caveats[1];
  assert.match(text, /run `kb setup --remove <harness>` for each harness\./);
  assert.match(
    text,
    /stay after the uninstall, in \$KNOWLEDGE_MCP_STATE_DIR when set,\s+else \$XDG_STATE_HOME\/knowledge-mcp, else ~\/\.local\/state\/knowledge-mcp\./,
  );
  assert.match(text, /`kb doctor` shows the folder in use\./);
  // The history folder stays: the caveats offer no command that deletes it.
  assert.doesNotMatch(text, /rm -r/);
});

test("ruby reads the formula", (context) => {
  const ruby = spawnSync("ruby", ["--version"], { encoding: "utf8" });
  if (ruby.status !== 0) {
    context.skip("ruby is not installed");
    return;
  }
  const dir = mkdtempSync(join(tmpdir(), "formula-"));
  const path = join(dir, "knowledge-mcp.rb");
  writeFileSync(path, formula());
  const checked = spawnSync("ruby", ["-c", path], { encoding: "utf8" });
  assert.equal(checked.status, 0, checked.stderr);
  assert.match(checked.stdout, /Syntax OK/);
});

test("markers are read for CPython 3.14 on macOS", () => {
  assert.equal(evaluate("sys_platform == 'win32'"), false);
  assert.equal(evaluate("sys_platform != 'emscripten'"), true);
  assert.equal(
    evaluate(
      "implementation_name != 'PyPy' and platform_python_implementation != 'PyPy'",
    ),
    true,
  );
  assert.equal(
    evaluate("(sys_platform == 'linux' or sys_platform == 'darwin')"),
    true,
  );
  assert.equal(evaluate("python_version < '3.11'"), false);
  assert.equal(evaluate("python_version >= '3.14'"), true);
});

test("requirements without an environment marker remain included", () => {
  assert.deepEqual(requirementsFor("example==1.2.3\n"), [
    { name: "example", version: "1.2.3" },
  ]);
});

test("an incomplete environment marker cannot produce a formula", () => {
  const dir = mkdtempSync(join(tmpdir(), "formula-"));
  const archive = join(dir, "archive.tar.gz");
  const out = join(dir, "knowledge-mcp.rb");
  writeFileSync(archive, sdist);
  writeFileSync(
    join(dir, "requirements.lock"),
    "example==1.2.3 ; python_version >=\n",
  );
  const { status, output } = run(
    "--sdist",
    archive,
    "--out",
    out,
    "--requirements",
    join(dir, "requirements.lock"),
  );
  assert.equal(status, 1);
  assert.match(output, /marker ends early/);
  assert.equal(existsSync(out), false);
});

test("the command line writes the formula from the repo's locks", () => {
  const dir = mkdtempSync(join(tmpdir(), "formula-"));
  const archive = join(dir, `knowledge_mcp-${version}.tar.gz`);
  writeFileSync(archive, sdist);
  const out = join(dir, "knowledge-mcp.rb");
  const { status, output } = run("--sdist", archive, "--out", out);
  assert.equal(status, 0, output);
  assert.equal(readFileSync(out, "utf8"), formula());
});

test("refuses a package uv.lock holds no source archive for", () => {
  const dir = mkdtempSync(join(tmpdir(), "formula-"));
  const archive = join(dir, "archive.tar.gz");
  writeFileSync(archive, sdist);
  writeFileSync(
    join(dir, "requirements.lock"),
    "wheel-only==1.0 \\\n    --hash=sha256:00\n",
  );
  writeFileSync(
    join(dir, "uv.lock"),
    'version = 1\n\n[[package]]\nname = "wheel-only"\nversion = "1.0"\nsource = { registry = "https://pypi.org/simple" }\nwheels = [{ url = "https://example.com/wheel_only-1.0-py3-none-any.whl", hash = "sha256:00" }]\n',
  );
  const { status, output } = run(
    "--sdist",
    archive,
    "--out",
    join(dir, "out.rb"),
    "--lock",
    join(dir, "uv.lock"),
    "--requirements",
    join(dir, "requirements.lock"),
  );
  assert.equal(status, 1);
  assert.match(output, /no source archive for wheel-only 1\.0/);
});

test("refuses a release asset of another version", () => {
  const dir = mkdtempSync(join(tmpdir(), "formula-"));
  const archive = join(dir, "archive.tar.gz");
  writeFileSync(archive, sdist);
  const { status, output } = run(
    "--sdist",
    archive,
    "--out",
    join(dir, "out.rb"),
    "--url",
    "https://example.com/knowledge_mcp-9.9.9.tar.gz",
  );
  assert.equal(status, 1);
  assert.match(
    output,
    new RegExp(`not the source archive of knowledge-mcp ${version}`),
  );
});

test("invalid requirements raise a library error without terminating its caller", () => {
  assert.throws(
    () => requirementsFor("invalid requirement\n"),
    /requirements.lock/,
  );
});
