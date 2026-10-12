import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";

import { stage } from "./bottle-assets.ts";
import { publish, restore } from "./published-bottles.ts";
import type { Run } from "./published-bottles.ts";

const version = "0.2.0";
const rootUrl =
  "https://github.com/SterlingJF/knowledge-mcp/releases/download/v0.2.0";
const identity = {
  version,
  rootUrl,
  repo: "SterlingJF/knowledge-mcp",
  releaseTag: "v0.2.0",
};
const tags = ["arm64_sequoia", "sequoia"];
const bytes = Buffer.from("native bottle fixture bytes\n");

function temp(context: TestContext): string {
  const dir = mkdtempSync(join(tmpdir(), "native-pair-test-"));
  context.after(() => rmSync(dir, { recursive: true, force: true }));
  return dir;
}

function fixture(dir: string, tag = tags[0]) {
  mkdirSync(dir, { recursive: true });
  const local = `knowledge-mcp--${version}.${tag}.bottle.tar.gz`;
  const remote = `knowledge-mcp-${version}.${tag}.bottle.tar.gz`;
  const json = `knowledge-mcp--${version}.${tag}.bottle.json`;
  const metadata =
    JSON.stringify(
      {
        "local/release/knowledge-mcp": {
          formula: {
            name: "knowledge-mcp",
            pkg_version: version,
            path: "Library/Taps/local/homebrew-release/Formula/knowledge-mcp.rb",
            tap_git_path: "Formula/knowledge-mcp.rb",
          },
          bottle: {
            root_url: rootUrl,
            cellar: tag === "sequoia" ? "/usr/local/Cellar" : "any",
            rebuild: 0,
            tags: {
              [tag]: {
                filename: remote,
                local_filename: local,
                sha256: createHash("sha256").update(bytes).digest("hex"),
                tab: {
                  built_prefix:
                    tag === "sequoia" ? "/usr/local" : "/opt/homebrew",
                },
                binary_relocation_diagnostics: [
                  { path: "libexec/bin/kb", reason: "original native detail" },
                ],
              },
            },
          },
        },
      },
      null,
      2,
    ) + "\n";
  writeFileSync(join(dir, local), bytes);
  writeFileSync(join(dir, json), metadata);
  return {
    local,
    remote,
    json,
    metadata,
    paths: stage({
      version,
      rootUrl,
      tag,
      metadata: join(dir, json),
      out: join(dir, "staged"),
    }),
  };
}

function remoteRunner(files: Map<string, string>, events: Array<string>): Run {
  return (args) => {
    assert.equal(args.includes("--clobber"), false);
    if (args[0] !== "release") throw new Error("Unexpected command");
    if (args[1] === "view")
      return JSON.stringify({
        assets: [...files.keys()].map((name) => ({ name })),
      });
    if (args[1] === "upload") {
      const path = args[3];
      const name = basename(path);
      assert.equal(
        files.has(name),
        false,
        "existing release assets cannot be uploaded again",
      );
      files.set(name, path);
      events.push(`upload:${name}`);
      return "";
    }
    assert.equal(
      args[1],
      "download",
      "the mock only implements named release operations",
    );
    const name = args[args.indexOf("--pattern") + 1];
    const source = files.get(name);
    assert.ok(source, `missing fixture asset: ${name}`);
    copyFileSync(source, join(args[args.indexOf("--dir") + 1], name));
    events.push(`verify:${name}`);
    return "";
  };
}

test("a complete native JSON/archive pair restores unchanged metadata and verified original bytes", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  const remote = new Map([
    [item.json, item.paths[2]],
    [item.remote, item.paths[0]],
  ]);
  const out = join(dir, "restored");
  assert.equal(
    restore({ ...identity, tag: tags[0], out }, remoteRunner(remote, [])),
    true,
  );
  assert.deepEqual(
    readdirSync(out).sort(),
    [item.local, item.remote, item.json].sort(),
  );
  assert.equal(readFileSync(join(out, item.json), "utf8"), item.metadata);
  assert.deepEqual(readFileSync(join(out, item.local)), bytes);
});

test("an absent native pair selects a fresh build without creating output", (context) => {
  const dir = temp(context);
  const out = join(dir, "restored");
  const events: Array<string> = [];
  assert.equal(
    restore(
      { ...identity, tag: tags[0], out },
      remoteRunner(new Map(), events),
    ),
    false,
  );
  assert.equal(existsSync(out), false);
  assert.deepEqual(events, []);
});

for (const member of ["json", "remote"] as const) {
  test(`a fresh dispatch refuses a pair missing its ${member === "json" ? "archive" : "metadata"} partner`, (context) => {
    const dir = temp(context);
    const item = fixture(join(dir, "original"));
    const remote = new Map([
      [item[member], member === "json" ? item.paths[2] : item.paths[0]],
    ]);
    assert.throws(
      () =>
        restore(
          { ...identity, tag: tags[0], out: join(dir, "restored") },
          remoteRunner(remote, []),
        ),
      /rerun failed jobs.*Actions artifacts/i,
    );
    assert.equal(existsSync(join(dir, "restored")), false);
  });
}

test("restore rejects wrong metadata identity and archive hashes before staging", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  const remote = new Map([
    [item.json, item.paths[2]],
    [item.remote, item.paths[0]],
  ]);
  writeFileSync(item.paths[0], "corrupt");
  assert.throws(
    () =>
      restore(
        { ...identity, tag: tags[0], out: join(dir, "restored") },
        remoteRunner(remote, []),
      ),
    /SHA-256 mismatch/,
  );
  assert.equal(existsSync(join(dir, "restored")), false);
  writeFileSync(item.paths[0], bytes);
  writeFileSync(
    item.paths[2],
    item.metadata.replace('"pkg_version": "0.2.0"', '"pkg_version": "0.3.0"'),
  );
  assert.throws(
    () =>
      restore(
        { ...identity, tag: tags[0], out: join(dir, "restored") },
        remoteRunner(remote, []),
      ),
    /version/,
  );
});

test("publication verifies every native JSON before uploading either canonical archive", (context) => {
  const dir = temp(context);
  const artifacts = join(dir, "artifacts");
  mkdirSync(artifacts);
  const items = tags.map((tag) => fixture(join(dir, tag), tag));
  for (const item of items)
    for (const path of item.paths)
      copyFileSync(path, join(artifacts, basename(path)));
  const events: Array<string> = [];
  publish(
    { ...identity, dir: artifacts, tags },
    remoteRunner(new Map(), events),
  );
  for (const item of items)
    assert.ok(
      events.indexOf(`verify:${item.json}`) <
        events.indexOf(`upload:${items[0].remote}`),
    );
  assert.equal(events.filter((event) => event.startsWith("upload:")).length, 4);
  assert.equal(
    events.some((event) => event.includes("recovery")),
    false,
  );
});

test("a failed native JSON verification prevents all canonical archive uploads", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  const events: Array<string> = [];
  const existing = join(dir, "wrong.json");
  writeFileSync(
    existing,
    item.metadata.replace("original native detail", "changed native detail"),
  );
  const remote = new Map([[item.json, existing]]);
  assert.throws(
    () =>
      publish(
        { ...identity, dir: join(dir, "original/staged"), tags: [tags[0]] },
        remoteRunner(remote, events),
      ),
    /published.*differs/i,
  );
  assert.equal(
    events.some((event) => event.startsWith("upload:")),
    false,
  );
});

test("a failed-job retry completes metadata-only publication from retained exact Actions artifacts", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  const remote = new Map([[item.json, item.paths[2]]]);
  const events: Array<string> = [];
  publish(
    { ...identity, dir: join(dir, "original/staged"), tags: [tags[0]] },
    remoteRunner(remote, events),
  );
  assert.deepEqual(events, [
    `verify:${item.json}`,
    `upload:${item.remote}`,
    `verify:${item.remote}`,
  ]);
});

test("complete published pairs are reverified without overwrite and inventory errors are not absence", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  const remote = new Map([
    [item.json, item.paths[2]],
    [item.remote, item.paths[0]],
  ]);
  const events: Array<string> = [];
  publish(
    { ...identity, dir: join(dir, "original/staged"), tags: [tags[0]] },
    remoteRunner(remote, events),
  );
  assert.ok(events.every((event) => event.startsWith("verify:")));
  assert.throws(
    () =>
      restore({ ...identity, tag: tags[0], out: join(dir, "out") }, () => {
        throw new Error("inventory failed");
      }),
    /inventory failed/,
  );
});

test("invalid local artifacts cannot cause a remote write", (context) => {
  const dir = temp(context);
  const item = fixture(join(dir, "original"));
  writeFileSync(item.paths[0], "wrong bytes");
  let calls = 0;
  assert.throws(
    () =>
      publish(
        { ...identity, dir: join(dir, "original/staged"), tags: [tags[0]] },
        () => {
          calls++;
          return "";
        },
      ),
    /SHA-256/,
  );
  assert.equal(calls, 0);
});
