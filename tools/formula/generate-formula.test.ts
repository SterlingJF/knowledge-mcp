import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { parse } from "smol-toml";

import {
  evaluate,
  generate,
  requirementsFor,
  resolve as resourcesFor,
} from "./generate-formula.ts";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const script = join(here, "generate-formula.ts");
const lock = readFileSync(join(root, "uv.lock"), "utf8");
const requirements = execFileSync(
  "uv",
  [
    "export",
    "--color",
    "never",
    "--project",
    root,
    "--locked",
    "--package",
    "knowledge-mcp",
    "--no-dev",
    "--no-emit-workspace",
    "--no-header",
    "--format",
    "requirements-txt",
  ],
  { encoding: "utf8" },
);
const pyproject = readFileSync(join(root, "runtime/pyproject.toml"), "utf8");
const version = /^version = "([^"]+)"/m.exec(pyproject)![1];
const sdist = Buffer.from("a stand-in for the release's source archive\n");

function formula(): string {
  return generate({ sdist, lock, requirements, pyproject });
}

function run(...args: Array<string>) {
  const dir = mkdtempSync(join(tmpdir(), "formula-export-"));
  const exported = join(dir, "requirements.txt");
  writeFileSync(exported, requirements);
  const result = spawnSync(
    process.execPath,
    [script, "--requirements", exported, ...args],
    {
      cwd: root,
      encoding: "utf8",
    },
  );
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

test("knowledge-bus comes from its actual locked archive with the hash uv.lock holds", () => {
  const block =
    /resource "knowledge-bus" do\n {4}url "([^"]+)"\n {4}sha256 "([0-9a-f]{64})"\n {2}end/.exec(
      formula(),
    );
  assert.ok(block);
  const entry = (
    parse(lock) as {
      package: Array<{ name: string; source: { url?: string; path?: string } }>;
    }
  ).package.find((item) => item.name === "knowledge-bus")!;
  assert.equal(
    block[1],
    entry.source.url ?? pathToFileURL(resolve(root, entry.source.path!)).href,
  );
  assert.match(lock, new RegExp(`hash = "sha256:${block[2]}"`));
});

test("every macOS requirement becomes a source resource; other platforms' stay out", () => {
  const text = formula();
  const names = [...text.matchAll(/resource "([^"]+)" do/g)].map((m) => m[1]);
  const wanted = requirementsFor(requirements, lock, root).map((r) => r.name);
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
  assert.match(text, /depends_on "openssl@4"/);
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

test("Click completions use the installed wrapper and all three shells are checked", () => {
  const text = formula();
  assert.match(
    text,
    /KNOWLEDGE_MCP_DATA: +opt_libexec\/site_packages\/"knowledge_mcp"\n +generate_completions_from_executable\(bin\/"kb", shell_parameter_format: :click\)/,
  );
  const installedTest = /\n {2}test do\n([\s\S]*?)\n {2}end/.exec(text);
  assert.ok(installedTest);
  for (const path of [
    'bash_completion/"kb"',
    'zsh_completion/"_kb"',
    'fish_completion/"kb.fish"',
  ]) {
    assert.ok(installedTest[1].includes(`assert_path_exists ${path}`), path);
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
  // Uninstall instructions must preserve the user's history.
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
  assert.throws(() => requirementsFor("invalid requirement\n"), /uv export/);
});

function localFixture() {
  const directory = mkdtempSync(join(tmpdir(), "formula local "));
  const path = join(directory, "actual source #1.tar.gz");
  writeFileSync(path, sdist);
  const url = pathToFileURL(path).href;
  const hash = createHash("sha256").update(sdist).digest("hex");
  const localLock = `[[package]]
name = "known-package"
version = "1.2.3"
source = { path = ${JSON.stringify(path)} }
sdist = { hash = "sha256:${hash}" }
`;
  return { directory, path, url, hash, localLock };
}

test("bare local uv export binds name, version, normalized URL and actual hash from uv.lock", () => {
  const { url, hash, localLock } = localFixture();
  const selected = requirementsFor(
    `${url} \
    --hash=sha256:${hash} ; sys_platform == 'darwin'`,
    localLock,
  );
  assert.deepEqual(selected, [
    { name: "known-package", version: "1.2.3", url },
  ]);
  assert.deepEqual(resourcesFor(selected, localLock), [
    { name: "known-package", url, sha256: hash },
  ]);
  assert.match(
    generate({ sdist, lock: localLock, requirements: url, pyproject }),
    /resource "known-package"/,
  );
});

test("relative locked paths require the explicit lock directory and use standard file URL escaping", () => {
  const { directory, path, url, localLock } = localFixture();
  const relative = localLock.replace(
    JSON.stringify(path),
    JSON.stringify("actual source #1.tar.gz"),
  );
  assert.throws(() => requirementsFor(url, relative), /uv.lock directory/);
  assert.deepEqual(requirementsFor(url, relative, directory), [
    { name: "known-package", version: "1.2.3", url },
  ]);
  assert.equal(
    resourcesFor(
      requirementsFor(url, relative, directory),
      relative,
      directory,
    )[0].url,
    url,
  );
});

test("local requirements reject unbound paths, ambiguous bindings, and missing metadata", () => {
  const { url, localLock } = localFixture();
  for (const text of [
    undefined,
    "",
    localLock + localLock,
    localLock.replace('name = "known-package"', 'name = ""'),
    localLock.replace('version = "1.2.3"', 'version = ""'),
    localLock.replace(/sdist = .+/, ""),
    localLock.replace(/sha256:[a-f0-9]+/, "sha256:00"),
  ])
    assert.throws(() => requirementsFor(url, text), /bind|bound/);
  assert.throws(
    () => requirementsFor(url.replace("source", "other"), localLock),
    /bind/,
  );
  for (const bad of [
    url + "?q=1",
    url + "#fragment",
    url.replace("file:///", "file://remote/"),
  ]) {
    assert.throws(() => requirementsFor(bad, localLock), /unsupported/);
  }
  assert.throws(
    () => requirementsFor("https://example.invalid/package.tar.gz", localLock),
    /uv export/,
  );
});

test("local archive and export hashes must match the locked source before formula output", () => {
  const { path, url, hash, localLock } = localFixture();
  assert.throws(
    () => requirementsFor(`${url} --hash=sha256:${"0".repeat(64)}`, localLock),
    /hash differs/,
  );
  const input = requirementsFor(url, localLock);
  writeFileSync(path, Buffer.concat([sdist, Buffer.from("changed")]));
  assert.throws(() => requirementsFor(url, localLock), /hash differs/);
  assert.throws(() => resourcesFor(input, localLock), /hash differs/);
  assert.throws(
    () => generate({ sdist, lock: localLock, requirements: url, pyproject }),
    /hash differs/,
  );
  assert.equal(input[0].version, "1.2.3");
  assert.equal(hash.length, 64);
});

test("local named requirements cannot disagree with the locked name, version or source", () => {
  const { url, localLock } = localFixture();
  for (const requirement of [
    { name: "other", url },
    { name: "known-package", version: "9.9.9", url },
    { name: "known-package", url: url.replace("source", "other") },
  ])
    assert.throws(
      () => resourcesFor([requirement], localLock),
      /uv.lock has no/,
    );
  const mismatch = localLock.replace(
    "sdist = {",
    `sdist = { url = "file:///different.tar.gz",`,
  );
  assert.throws(() => requirementsFor(url, mismatch), /bound/);
});

test("normalized resource collisions fail before rendering", () => {
  const { url, localLock } = localFixture();
  const input = requirementsFor(url, localLock);
  assert.throws(
    () => resourcesFor([...input, ...input], localLock),
    /duplicate formula resource/,
  );
  const alias = localLock.replace(
    'name = "known-package"',
    'name = "known_package"',
  );
  assert.throws(() => requirementsFor(url, localLock + alias), /exactly one/);
});

test("published URL resources retain the existing rendered bytes", () => {
  const url = "https://example.com/known-package-1.2.3.tar.gz";
  const hash = "a".repeat(64);
  const remoteLock = `[[package]]
name = "known-package"
version = "1.2.3"
source = { url = "${url}" }
sdist = { url = "${url}", hash = "sha256:${hash}" }
`;
  const pinned = generate({
    sdist,
    lock: remoteLock,
    requirements: "known-package==1.2.3",
    pyproject,
  });
  const direct = generate({
    sdist,
    lock: remoteLock,
    requirements: `known-package @ ${url}`,
    pyproject,
  });
  assert.equal(direct, pinned);
  assert.deepEqual(
    resourcesFor(requirementsFor(`known-package @ ${url}`), remoteLock),
    [{ name: "known-package", url, sha256: hash }],
  );
});
