import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import childProcess, { execFileSync, spawnSync } from "node:child_process";
import type { SpawnSyncReturns } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { syncBuiltinESMExports } from "node:module";
import { basename, join, resolve } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";

import {
  bottle,
  CommandError,
  merge,
  source,
  target,
  tap,
  verifyInstalls,
} from "./release.ts";
import type { Release, Runner } from "./release.ts";

const repository = "SterlingJF/knowledge-mcp";
const projectRoot = resolve(import.meta.dirname, "../..");

function temporary(context: TestContext): string {
  const root = mkdtempSync(join(tmpdir(), "release-policy-test-"));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  return root;
}

function git(root: string, args: Array<string>): string {
  return execFileSync(
    "git",
    [
      "-c",
      "core.hooksPath=/dev/null",
      "-c",
      "commit.gpgsign=false",
      "-c",
      "user.name=Release Test",
      "-c",
      "user.email=release-test@example.invalid",
      ...args,
    ],
    { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  ).trim();
}

function releasedSource(context: TestContext) {
  const root = temporary(context);
  const checkout = join(root, "release-source");
  mkdirSync(join(checkout, "runtime"), { recursive: true });
  for (const file of [
    "uv.lock",
    "runtime/pyproject.toml",
    "runtime/requirements.lock",
  ])
    copyFileSync(join(projectRoot, file), join(checkout, file));
  git(checkout, ["init", "-q"]);
  git(checkout, ["add", "."]);
  git(checkout, ["commit", "-qm", "released source"]);
  const commit = git(checkout, ["rev-parse", "HEAD"]);
  git(checkout, ["tag", "v0.2.0"]);
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit,
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  return { root, checkout, release };
}

test("target resolves the tag's immutable manifest even when the current branch differs", async (context) => {
  const fixture = releasedSource(context);
  const manifest = join(fixture.checkout, "runtime/pyproject.toml");
  writeFileSync(
    manifest,
    readFileSync(manifest, "utf8").replace(
      'version = "0.2.0"',
      'version = "0.3.0"',
    ),
  );
  git(fixture.checkout, ["add", "."]);
  git(fixture.checkout, ["commit", "-qm", "unreleased branch"]);
  const run: Runner = (command, args) => {
    assert.equal(command, "git");
    return git(fixture.checkout, args);
  };
  const result = await target(
    { tag: "v0.2.0", repo: repository, root: fixture.root },
    run,
  );
  assert.deepEqual(result, fixture.release);
  assert.deepEqual(
    JSON.parse(readFileSync(join(fixture.root, "dist/release.json"), "utf8")),
    fixture.release,
  );
});

test("invalid tags and package mismatches cannot produce release state", async (context) => {
  const fixture = releasedSource(context);
  let calls = 0;
  const run: Runner = (command, args) => {
    calls++;
    assert.equal(command, "git");
    return git(fixture.checkout, args);
  };
  await assert.rejects(
    target({ tag: "v0.2.0;other", repo: repository, root: fixture.root }, run),
    /stable|tag/,
  );
  assert.equal(calls, 0);
  git(fixture.checkout, ["tag", "v0.3.0"]);
  await assert.rejects(
    target({ tag: "v0.3.0", repo: repository, root: fixture.root }, run),
    /package version/,
  );
  assert.equal(existsSync(join(fixture.root, "dist/release.json")), false);
});

test("source reuses the immutable asset and generates from the released lockfiles", async (context) => {
  const fixture = releasedSource(context);
  const archive = Buffer.from("published source fixture\n");
  const events: Array<string> = [];
  const run: Runner = (command, args) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "git") return git(fixture.checkout, args);
    if (command === "tar") return "Name: knowledge-mcp\nVersion: 0.2.0\n";
    assert.equal(command, "gh");
    if (args[0] === "api")
      return (
        "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" +
        JSON.stringify({ assets: [{ name: "knowledge_mcp-0.2.0.tar.gz" }] })
      );
    assert.equal(args[1], "download");
    writeFileSync(
      join(args[args.indexOf("--dir") + 1], "knowledge_mcp-0.2.0.tar.gz"),
      archive,
    );
    return "";
  };
  await source(
    { release: fixture.release, source: fixture.checkout, root: fixture.root },
    run,
  );
  assert.deepEqual(
    readFileSync(join(fixture.root, "dist/knowledge_mcp-0.2.0.tar.gz")),
    archive,
  );
  const formula = readFileSync(
    join(fixture.root, "dist/knowledge-mcp.rb"),
    "utf8",
  );
  assert.match(formula, /knowledge_mcp-0\.2\.0\.tar\.gz/);
  assert.match(formula, /resource "knowledge-bus"/);
  assert.equal(
    events.some((event) => event.startsWith("just ")),
    false,
    "published source is never rebuilt",
  );
  assert.equal(
    events.some((event) => event.includes("upload")),
    false,
  );
});

test("source builds through the existing root recipe and refuses the wrong checkout before publication", async (context) => {
  const fixture = releasedSource(context);
  const events: Array<string> = [];
  const run: Runner = (command, args) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "git") return git(fixture.checkout, args);
    if (command === "tar") return "Name: knowledge-mcp\nVersion: 0.2.0\n";
    if (command === "just") {
      assert.deepEqual(args, [
        "build_knowledge_mcp",
        fixture.checkout,
        join(fixture.root, "dist"),
      ]);
      writeFileSync(
        join(fixture.root, "dist/knowledge_mcp-0.2.0.tar.gz"),
        "new source fixture",
      );
      return "";
    }
    assert.equal(command, "gh");
    if (args[0] === "api")
      return "HTTP/2.0 200 OK\n\n" + JSON.stringify({ assets: [] });
    assert.equal(args[1], "upload");
    assert.equal(args.includes("--clobber"), false);
    return "";
  };
  await source(
    { release: fixture.release, source: fixture.checkout, root: fixture.root },
    run,
  );
  assert.ok(
    events.find((event) => event.startsWith("just build_knowledge_mcp")),
  );
  events.length = 0;
  const wrong = { ...fixture.release, commit: "0".repeat(40) };
  await assert.rejects(
    source(
      { release: wrong, source: fixture.checkout, root: fixture.root },
      run,
    ),
    /checkout/,
  );
  assert.ok(events.every((event) => event.startsWith("git ")));
});

test("a reused source archive with the wrong package identity cannot produce a formula", async (context) => {
  const fixture = releasedSource(context);
  const run: Runner = (command, args) => {
    if (command === "git") return git(fixture.checkout, args);
    if (command === "tar") return "Name: other-package\nVersion: 0.2.0\n";
    assert.equal(command, "gh");
    if (args[0] === "api")
      return (
        "HTTP/2.0 200 OK\n\n" +
        JSON.stringify({ assets: [{ name: "knowledge_mcp-0.2.0.tar.gz" }] })
      );
    assert.equal(args[1], "download");
    writeFileSync(
      join(args[args.indexOf("--dir") + 1], "knowledge_mcp-0.2.0.tar.gz"),
      "source fixture",
    );
    return "";
  };
  await assert.rejects(
    source(
      {
        release: fixture.release,
        source: fixture.checkout,
        root: fixture.root,
      },
      run,
    ),
    /source archive/,
  );
  assert.equal(existsSync(join(fixture.root, "dist/knowledge-mcp.rb")), false);
});

test("CLI rejects unknown stages and missing flags before invoking external commands", () => {
  const cli = new URL("./release.ts", import.meta.url);
  for (const args of [["unknown"], ["target", "--tag", "v0.2.0"]]) {
    const result = spawnSync(process.execPath, [cli.pathname, ...args], {
      encoding: "utf8",
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /stage|repo|required|Usage/);
  }
});

test("verification uses ordinary bottle installs and keeps failures out of successful reports", async (context) => {
  const fixture = releasedSource(context);
  const root = fixture.root;
  mkdirSync(join(root, "dist"));
  writeFileSync(
    join(root, "dist/knowledge-mcp.rb"),
    "class KnowledgeMcp < Formula\nend\n",
  );
  let kind = "source";
  const installs: Array<Array<string>> = [];
  const lifecycle: Array<string> = [];
  const run: Runner = (command, args, options) => {
    lifecycle.push(`${command} ${args.join(" ")}`);
    if (command === "uname") return "arm64";
    if (command === "sw_vers") return "15.7";
    if (command === "brew") {
      if (args[0] === "--prefix")
        return args.length === 1 ? "/opt/homebrew" : join(root, "prefix");
      if (args[0] === "--repository") return join(root, "local-tap");
      if (args[0] === "tap-new") {
        mkdirSync(join(root, "local-tap/Formula"), { recursive: true });
        return "";
      }
      if (args[0] === "deps") return "python@3.14";
      if (args[0] === "--cache") return join(root, `${kind}.tar.gz`);
      if (
        args[0] === "install" &&
        args.includes("local/release/knowledge-mcp")
      ) {
        installs.push(args);
        kind = args.includes("--build-from-source") ? "source" : "bottle";
      }
      if (args[0] === "info")
        return JSON.stringify({
          formulae: [
            {
              installed: [
                { version: "0.2.0", poured_from_bottle: kind === "bottle" },
              ],
            },
          ],
        });
      if (options?.log) writeFileSync(options.log, "validation fixture\n");
      return "";
    }
    assert.equal(basename(command), "kb");
    if (options?.log) writeFileSync(options.log, "doctor fixture\n");
    return "kb 0.2.0";
  };
  await verifyInstalls(
    {
      release: fixture.release,
      root,
      arch: "arm64",
      prefix: "/opt/homebrew",
      bottleTag: "arm64_sequoia",
    },
    run,
  );
  assert.deepEqual(installs, [
    ["install", "--build-from-source", "local/release/knowledge-mcp"],
    ["install", "local/release/knowledge-mcp"],
  ]);
  const trusted = lifecycle.indexOf(
    "brew trust --formula local/release/knowledge-mcp",
  );
  assert.ok(trusted >= 0, "the copied local formula is explicitly trusted");
  for (const operation of ["audit", "deps", "info"])
    assert.ok(
      trusted <
        lifecycle.findIndex((call) => call.startsWith(`brew ${operation} `)),
      "trust precedes formula loading",
    );
  assert.ok(
    lifecycle.indexOf("brew uninstall local/release/knowledge-mcp") <
      lifecycle.indexOf(
        "brew install --build-from-source local/release/knowledge-mcp",
      ),
    "an existing app is removed before either timed install",
  );
  for (const path of [
    "source-install.json",
    "bottle-install.json",
    "source-test.log",
    "bottle-doctor.log",
  ])
    assert.equal(existsSync(join(root, "install-reports", path)), true);
});

test("tap refuses changed same-version source before copying or committing", (context) => {
  const fixture = releasedSource(context);
  mkdirSync(join(fixture.root, "dist"));
  mkdirSync(join(fixture.root, "tap/Formula"), { recursive: true });
  writeFileSync(
    join(fixture.root, "dist/knowledge-mcp.rb"),
    "candidate formula\n",
  );
  const current = join(fixture.root, "tap/Formula/knowledge-mcp.rb");
  writeFileSync(current, "current formula\n");
  const events: Array<string> = [];
  const trusted = new Set<string>();
  const run: Runner = (command, args) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "brew" && args[0] === "tap-new") {
      mkdirSync(
        join(
          fixture.root,
          args[2] === "local/current" ? "current/Formula" : "candidate/Formula",
        ),
        { recursive: true },
      );
      return "";
    }
    if (command === "brew" && args[0] === "--repository")
      return join(
        fixture.root,
        args[1] === "local/current" ? "current" : "candidate",
      );
    if (command === "brew" && args[0] === "trust") {
      assert.equal(args[1], "--formula");
      trusted.add(args[2]);
      const copied =
        args[2] === "local/current/knowledge-mcp" ? "current" : "candidate";
      assert.equal(
        readFileSync(
          join(fixture.root, copied, "Formula/knowledge-mcp.rb"),
          "utf8",
        ),
        `${copied} formula\n`,
      );
      return "";
    }
    if (command === "brew" && args[0] === "info") {
      assert.ok(
        trusted.has(args.at(-1) ?? ""),
        "only the copied formula is trusted before loading",
      );
      return JSON.stringify({
        formulae: [
          {
            name: "knowledge-mcp",
            versions: { stable: "0.2.0" },
            revision: 0,
            urls: {
              stable: {
                url: args.includes("local/current/knowledge-mcp")
                  ? "https://example.invalid/changed"
                  : `${fixture.release.rootUrl}/knowledge_mcp-0.2.0.tar.gz`,
                checksum: "a".repeat(64),
              },
            },
          },
        ],
      });
    }
    throw new Error("Unexpected command before source guard");
  };
  assert.throws(
    () =>
      tap(
        {
          release: fixture.release,
          root: fixture.root,
          tap: join(fixture.root, "tap"),
        },
        run,
      ),
    /source URL/,
  );
  assert.equal(readFileSync(current, "utf8"), "current formula\n");
  assert.ok(events.every((event) => !event.startsWith("git ")));
});

test("merge cannot publish when the required native matrix is incomplete", (context) => {
  const fixture = releasedSource(context);
  mkdirSync(join(fixture.root, "bottles"));
  let calls = 0;
  assert.throws(
    () =>
      merge({ release: fixture.release, root: fixture.root }, () => {
        calls++;
        return "";
      }),
    /missing bottle tags/,
  );
  assert.equal(calls, 0);
});

test("retrying local verification reuses the existing local tap", (context) => {
  const root = temporary(context);
  mkdirSync(join(root, "dist"));
  writeFileSync(join(root, "dist/knowledge-mcp.rb"), "candidate formula\n");
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit: "a".repeat(40),
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  const run: Runner = (command, args) => {
    if (command === "uname") return "arm64";
    if (command === "sw_vers") return "15.7";
    assert.equal(command, "brew");
    if (args[0] === "--prefix") return "/opt/homebrew";
    if (args[0] === "--repository") return join(root, "local-tap");
    if (args[0] === "tap-new") {
      if (existsSync(join(root, "local-tap")))
        throw new Error("Tap already installed");
      mkdirSync(join(root, "local-tap/Formula"), { recursive: true });
      return "";
    }
    if (args[0] === "deps") throw new Error("dependency setup failed");
    if (args[0] === "audit" || args[0] === "trust") return "";
    throw new Error("Unexpected command");
  };
  const options = {
    release,
    root,
    arch: "arm64",
    prefix: "/opt/homebrew",
    bottleTag: "arm64_sequoia",
  };
  assert.throws(() => verifyInstalls(options, run), /dependency setup failed/);
  assert.throws(() => verifyInstalls(options, run), /dependency setup failed/);
});

for (const name of ["local/release", "local/candidate", "local/current"]) {
  test(`a failed formula trust for ${name} stops before loading or updating the tap`, (context) => {
    const root = temporary(context);
    const release: Release = {
      tag: "v0.2.0",
      version: "0.2.0",
      commit: "a".repeat(40),
      repo: repository,
      rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
    };
    mkdirSync(join(root, "dist"));
    writeFileSync(join(root, "dist/knowledge-mcp.rb"), "candidate formula\n");
    const tapRoot = join(root, "tap");
    mkdirSync(join(tapRoot, "Formula"), { recursive: true });
    const current = join(tapRoot, "Formula/knowledge-mcp.rb");
    writeFileSync(current, "current formula\n");
    const calls: Array<string> = [];
    const trusted = new Set<string>();
    const run: Runner = (command, args, options) => {
      calls.push(`${command} ${args.join(" ")}`);
      if (command === "uname") return "arm64";
      if (command === "sw_vers") return "15.7";
      assert.equal(command, "brew");
      if (args[0] === "--prefix") return "/opt/homebrew";
      if (args[0] === "--repository") return join(root, args[1]);
      if (args[0] === "tap-new") {
        mkdirSync(join(root, args[2], "Formula"), { recursive: true });
        return "";
      }
      if (args[0] === "trust") {
        assert.deepEqual(args.slice(0, 2), ["trust", "--formula"]);
        assert.equal(args.length, 3);
        assert.equal(options?.log, join(root, "dist/formula-trust.log"));
        assert.equal(
          readFileSync(
            join(
              root,
              args[2].replace(/\/knowledge-mcp$/, ""),
              "Formula/knowledge-mcp.rb",
            ),
            "utf8",
          ),
          args[2] === "local/current/knowledge-mcp"
            ? "current formula\n"
            : "candidate formula\n",
        );
        if (args[2] === `${name}/knowledge-mcp`)
          throw new Error("formula trust failed");
        trusted.add(args[2]);
        return "";
      }
      assert.deepEqual(args, [
        "info",
        "--json=v2",
        "--formula",
        "local/candidate/knowledge-mcp",
      ]);
      assert.ok(trusted.has("local/candidate/knowledge-mcp"));
      return JSON.stringify({
        formulae: [
          {
            name: "knowledge-mcp",
            versions: { stable: release.version },
            revision: 0,
            urls: {
              stable: {
                url: `${release.rootUrl}/knowledge_mcp-${release.version}.tar.gz`,
                checksum: "a".repeat(64),
              },
            },
          },
        ],
      });
    };
    assert.throws(
      () =>
        name === "local/release"
          ? verifyInstalls(
              {
                release,
                root,
                arch: "arm64",
                prefix: "/opt/homebrew",
                bottleTag: "arm64_sequoia",
              },
              run,
            )
          : tap({ release, root, tap: tapRoot }, run),
      /formula trust failed/,
    );
    assert.equal(calls.at(-1), `brew trust --formula ${name}/knowledge-mcp`);
    assert.equal(readFileSync(current, "utf8"), "current formula\n");
    assert.equal(
      readFileSync(join(root, "dist/knowledge-mcp.rb"), "utf8"),
      "candidate formula\n",
    );
    assert.ok(calls.every((call) => !call.startsWith("git ")));
  });
}

test("a structured 404 creates the release, while authentication and transport failures cannot publish", async (context) => {
  const fixture = releasedSource(context);
  const events: Array<string> = [];
  let status: number | undefined = 404;
  const run: Runner = (command, args) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "git") return git(fixture.checkout, args);
    if (command === "tar") return "Name: knowledge-mcp\nVersion: 0.2.0\n";
    if (command === "just") {
      writeFileSync(
        join(fixture.root, "dist/knowledge_mcp-0.2.0.tar.gz"),
        "source fixture",
      );
      return "";
    }
    assert.equal(command, "gh");
    if (args[0] === "api")
      throw new CommandError(
        "gh",
        "api",
        status === undefined
          ? ""
          : `HTTP/2.0 ${status} Response\r\nContent-Type: application/json\r\n\r\n${JSON.stringify({ message: "native error fixture" })}`,
      );
    assert.ok(args[1] === "create" || args[1] === "upload");
    return "";
  };
  await source(
    { release: fixture.release, source: fixture.checkout, root: fixture.root },
    run,
  );
  assert.ok(events.some((event) => event.startsWith("gh release create")));
  for (const failure of [401, 403, undefined]) {
    status = failure;
    events.length = 0;
    await assert.rejects(
      source(
        {
          release: fixture.release,
          source: fixture.checkout,
          root: fixture.root,
        },
        run,
      ),
      /gh api failed/,
    );
    assert.ok(
      events.every(
        (event) =>
          !event.startsWith("gh release create") &&
          !event.startsWith("gh release upload") &&
          !event.startsWith("just "),
      ),
    );
  }
});

function nativeBottle(root: string, release: Release, tag: string) {
  mkdirSync(root, { recursive: true });
  const bytes = Buffer.from("built native bottle fixture\n");
  const local = `knowledge-mcp--${release.version}.${tag}.bottle.tar.gz`;
  const remote = `knowledge-mcp-${release.version}.${tag}.bottle.tar.gz`;
  const json = `knowledge-mcp--${release.version}.${tag}.bottle.json`;
  const metadata = JSON.stringify({
    "local/release/knowledge-mcp": {
      formula: {
        name: "knowledge-mcp",
        pkg_version: release.version,
        path: "Library/Taps/local/homebrew-release/Formula/knowledge-mcp.rb",
        tap_git_path: "Formula/knowledge-mcp.rb",
      },
      bottle: {
        root_url: release.rootUrl,
        cellar: "any",
        rebuild: 0,
        tags: {
          [tag]: {
            filename: remote,
            local_filename: local,
            sha256: createHash("sha256").update(bytes).digest("hex"),
            tab: { arch: tag === "sequoia" ? "x86_64" : "arm64" },
          },
        },
      },
    },
  });
  writeFileSync(join(root, local), bytes);
  writeFileSync(join(root, remote), bytes);
  writeFileSync(join(root, json), metadata);
  return { local, remote, json, metadata };
}

test("native build tests the installed app before staging original Homebrew metadata", (context) => {
  const root = temporary(context);
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit: "a".repeat(40),
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  mkdirSync(join(root, "dist"));
  writeFileSync(join(root, "dist/knowledge-mcp.rb"), "candidate formula\n");
  const events: Array<string> = [];
  let metadata = "";
  const run: Runner = (command, args, options) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "uname") return "x86_64";
    if (command === "sw_vers") return "15.7";
    if (command === "gh") {
      assert.equal(args[1], "view");
      return JSON.stringify({ assets: [] });
    }
    assert.equal(command, "brew");
    if (args[0] === "--prefix") return "/usr/local";
    if (args[0] === "--repository") return join(root, "local-tap");
    if (args[0] === "tap-new")
      mkdirSync(join(root, "local-tap/Formula"), { recursive: true });
    if (args[0] === "bottle") {
      assert.deepEqual(args, [
        "bottle",
        "--json",
        "--no-rebuild",
        `--root-url=${release.rootUrl}`,
        "local/release/knowledge-mcp",
      ]);
      assert.equal(options?.cwd, join(root, "bottle-build"));
      metadata = nativeBottle(
        join(root, "bottle-build"),
        release,
        "sequoia",
      ).metadata;
    }
    return "";
  };
  bottle(
    {
      release,
      root,
      arch: "x86_64",
      prefix: "/usr/local",
      bottleTag: "sequoia",
    },
    run,
  );
  const generated = events.findIndex((event) =>
    event.startsWith("brew bottle "),
  );
  assert.ok(
    events.includes("brew trust --formula local/release/knowledge-mcp"),
  );
  assert.ok(
    events.indexOf("brew trust --formula local/release/knowledge-mcp") <
      events.findIndex((event) => event.startsWith("brew style ")),
  );
  for (const command of [
    "brew install --build-bottle",
    "brew test",
    "brew linkage --test",
  ])
    assert.ok(
      events.findIndex((event) => event.startsWith(command)) < generated,
    );
  assert.equal(
    readFileSync(
      join(root, "bottles/knowledge-mcp--0.2.0.sequoia.bottle.json"),
      "utf8",
    ),
    metadata,
  );
});

test("a complete published pair bypasses rebuilding on a matching native host", (context) => {
  const root = temporary(context);
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit: "a".repeat(40),
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  const original = join(root, "original");
  const item = nativeBottle(original, release, "arm64_sequoia");
  const run: Runner = (command, args) => {
    if (command === "uname") return "arm64";
    if (command === "sw_vers") return "15.7";
    if (command === "brew") {
      assert.deepEqual(args, ["--prefix"]);
      return "/opt/homebrew";
    }
    assert.equal(command, "gh");
    if (args[1] === "view")
      return JSON.stringify({
        assets: [{ name: item.json }, { name: item.remote }],
      });
    assert.equal(args[1], "download");
    const name = args[args.indexOf("--pattern") + 1];
    copyFileSync(
      join(original, name),
      join(args[args.indexOf("--dir") + 1], name),
    );
    return "";
  };
  bottle(
    {
      release,
      root,
      arch: "arm64",
      prefix: "/opt/homebrew",
      bottleTag: "arm64_sequoia",
    },
    run,
  );
  assert.equal(
    readFileSync(join(root, "bottles", item.json), "utf8"),
    item.metadata,
  );
});

test("merge passes both original JSON files to Homebrew after native-pair publication", (context) => {
  const root = temporary(context);
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit: "a".repeat(40),
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  mkdirSync(join(root, "dist"));
  writeFileSync(join(root, "dist/knowledge-mcp.rb"), "candidate formula\n");
  const items = ["arm64_sequoia", "sequoia"].map((tag) =>
    nativeBottle(join(root, "bottles"), release, tag),
  );
  const remote = new Map<string, string>();
  const events: Array<string> = [];
  let trusted = false;
  const run: Runner = (command, args) => {
    events.push(`${command} ${args.join(" ")}`);
    if (command === "gh") {
      if (args[1] === "view") return JSON.stringify({ assets: [] });
      if (args[1] === "upload") {
        remote.set(basename(args[3]), args[3]);
        return "";
      }
      assert.equal(args[1], "download");
      const name = args[args.indexOf("--pattern") + 1];
      const path = remote.get(name);
      assert.ok(path);
      copyFileSync(path, join(args[args.indexOf("--dir") + 1], name));
      return "";
    }
    assert.equal(command, "brew");
    if (args[0] === "--repository") return join(root, "local-tap");
    if (args[0] === "tap-new")
      mkdirSync(join(root, "local-tap/Formula"), { recursive: true });
    if (args[0] === "trust") {
      assert.deepEqual(args, [
        "trust",
        "--formula",
        "local/release/knowledge-mcp",
      ]);
      assert.equal(
        readFileSync(join(root, "local-tap/Formula/knowledge-mcp.rb"), "utf8"),
        "candidate formula\n",
      );
      trusted = true;
    }
    if (args[0] === "bottle") {
      assert.equal(
        trusted,
        true,
        "native merge loads only the explicitly trusted formula",
      );
      assert.deepEqual(args, [
        "bottle",
        "--merge",
        "--write",
        "--no-commit",
        "--no-all-checks",
        ...items.map((item) => join(root, "bottles", item.json)),
      ]);
      for (const item of items)
        assert.equal(
          readFileSync(join(root, "bottles", item.json), "utf8"),
          item.metadata,
        );
      writeFileSync(
        join(root, "local-tap/Formula/knowledge-mcp.rb"),
        "merged by Homebrew\n",
      );
    }
    return "";
  };
  merge({ release, root }, run);
  assert.ok(
    events.findLastIndex((event) => event.startsWith("gh release download")) <
      events.findIndex((event) => event.startsWith("brew bottle --merge")),
  );
  assert.equal(
    readFileSync(join(root, "dist/knowledge-mcp.rb"), "utf8"),
    "merged by Homebrew\n",
  );
});

test("a failed native merge prints and logs its diagnostics once and stops the stage", (context) => {
  const root = temporary(context);
  const release: Release = {
    tag: "v0.2.0",
    version: "0.2.0",
    commit: "a".repeat(40),
    repo: repository,
    rootUrl: `https://github.com/${repository}/releases/download/v0.2.0`,
  };
  mkdirSync(join(root, "dist"));
  const formula = join(root, "dist/knowledge-mcp.rb");
  writeFileSync(formula, "candidate formula\n");
  const items = ["arm64_sequoia", "sequoia"].map((tag) =>
    nativeBottle(join(root, "bottles"), release, tag),
  );
  const assets = new Map(
    items.flatMap((item) =>
      [item.json, item.remote].map((name) => [
        name,
        join(root, "bottles", name),
      ]),
    ),
  );
  const calls: Array<string> = [];
  const stdout: Array<string> = [];
  const stderr: Array<string> = [];
  const nativeOutput = "==> local/release/knowledge-mcp\n";
  const nativeError = "Error: native merge diagnostic\n";
  context.mock.method(process.stdout, "write", (chunk: string) => {
    stdout.push(chunk);
    return true;
  });
  context.mock.method(process.stderr, "write", (chunk: string) => {
    stderr.push(chunk);
    return true;
  });
  context.mock.method(
    childProcess,
    "spawnSync",
    (command: string, args: Array<string>): SpawnSyncReturns<string> => {
      calls.push(`${command} ${args.join(" ")}`);
      const result: SpawnSyncReturns<string> = {
        pid: 1,
        status: 0,
        signal: null,
        stdout: "",
        stderr: "",
        output: [null, "", ""],
      };
      if (command === "gh") {
        if (args[1] === "view") {
          result.stdout = JSON.stringify({
            assets: [...assets.keys()].map((name) => ({ name })),
          });
        } else {
          assert.equal(args[1], "download");
          const name = args[args.indexOf("--pattern") + 1];
          const path = assets.get(name);
          assert.ok(path);
          copyFileSync(path, join(args[args.indexOf("--dir") + 1], name));
        }
      } else {
        assert.equal(command, "brew");
        if (args[0] === "--repository") result.stdout = join(root, "local-tap");
        else if (args[0] === "tap-new")
          mkdirSync(join(root, "local-tap/Formula"), { recursive: true });
        else if (args[0] === "trust")
          assert.deepEqual(args, [
            "trust",
            "--formula",
            "local/release/knowledge-mcp",
          ]);
        else {
          assert.equal(args[0], "bottle");
          result.status = 1;
          result.stdout = nativeOutput;
          result.stderr = nativeError;
        }
      }
      return result;
    },
  );
  syncBuiltinESMExports();
  context.after(() => {
    context.mock.restoreAll();
    syncBuiltinESMExports();
  });
  assert.throws(() => merge({ release, root }), /brew bottle failed/);
  assert.equal(stdout.join(""), nativeOutput);
  assert.equal(stderr.join(""), nativeError);
  assert.equal(
    readFileSync(join(root, "bottles/merge.log"), "utf8"),
    nativeOutput + nativeError,
  );
  assert.equal(calls.at(-1)?.startsWith("brew bottle --merge"), true);
  assert.equal(readFileSync(formula, "utf8"), "candidate formula\n");
});
