import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";
import { fileURLToPath } from "node:url";

import { stage, verify } from "./bottle-assets.ts";

const version = "0.2.0";
const rootUrl =
  "https://github.com/SterlingJF/knowledge-mcp/releases/download/v0.2.0";
const fullName = "sterlingjf/tap/knowledge-mcp";
const expected = { version, rootUrl };
const tags = ["arm64_sequoia", "sequoia"];
const bytes = Buffer.from("stand-in bottle bytes\n");

function fixture(tag = tags[0], pkgVersion = version, rebuild = 0) {
  const suffix = `.${tag}.bottle${rebuild ? `.${rebuild}` : ""}.tar.gz`;
  return {
    [fullName]: {
      formula: {
        name: "knowledge-mcp",
        pkg_version: pkgVersion,
        path: "Library/Taps/sterlingjf/homebrew-tap/Formula/knowledge-mcp.rb",
        tap_git_path: "Formula/knowledge-mcp.rb",
        tap_git_revision: "cafe1234",
        tap_git_remote: "https://github.com/SterlingJF/homebrew-tap",
        desc: "Knowledge MCP",
        license: "MIT",
      },
      bottle: {
        root_url: rootUrl,
        cellar: tag.startsWith("arm64")
          ? "/opt/homebrew/Cellar"
          : "/usr/local/Cellar",
        rebuild,
        date: "2026-10-11T12:00:00Z",
        tags: {
          [tag]: {
            filename: encodeURIComponent(
              `knowledge-mcp-${pkgVersion}${suffix}`,
            ),
            local_filename: `knowledge-mcp--${pkgVersion}${suffix}`,
            sha256: createHash("sha256").update(bytes).digest("hex"),
            tab: {
              built_prefix: tag.startsWith("arm64")
                ? "/opt/homebrew"
                : "/usr/local",
              poured_from_bottle: false,
            },
            sbom: { spdxVersion: "SPDX-2.3" },
            all_files: ["bin/kb", "libexec/bin/kb"],
            binary_relocation_diagnostics: [
              { path: "libexec/bin/kb", reason: "built prefix" },
            ],
          },
        },
      },
    },
  };
}
type Fixture = Record<string, ReturnType<typeof fixture>[typeof fullName]>;

function temp(context: TestContext): string {
  const dir = mkdtempSync(join(tmpdir(), "bottle-assets-"));
  context.after(() => rmSync(dir, { recursive: true, force: true }));
  return dir;
}

function source(dir: string, data = fixture()): string {
  mkdirSync(dir, { recursive: true });
  const metadata = join(dir, "native.bottle.json");
  writeFileSync(metadata, JSON.stringify(data, null, 2) + "\n");
  const tagData = Object.values(data[fullName].bottle.tags)[0];
  writeFileSync(join(dir, tagData.local_filename), bytes);
  return metadata;
}

function matrix(dir: string): Array<string> {
  return tags.map((tag) => {
    const metadata = source(join(dir, "sources", tag), fixture(tag));
    return stage({
      ...expected,
      tag,
      metadata,
      out: join(dir, "artifacts", tag),
    })[2];
  });
}

function change(path: string, mutate: (data: Fixture) => void): void {
  const data = JSON.parse(readFileSync(path, "utf8")) as Fixture;
  mutate(data);
  writeFileSync(path, JSON.stringify(data));
}

test("stage preserves archive bytes and metadata under both Homebrew filenames", (context) => {
  const dir = temp(context);
  const metadata = source(join(dir, "source"));
  const out = join(dir, "artifacts");
  const paths = stage({ ...expected, metadata, tag: tags[0], out });
  assert.deepEqual(
    readdirSync(out).sort(),
    [
      "knowledge-mcp-0.2.0.arm64_sequoia.bottle.tar.gz",
      "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz",
      "knowledge-mcp--0.2.0.arm64_sequoia.bottle.json",
    ].sort(),
  );
  assert.deepEqual(readFileSync(paths[0]), bytes);
  assert.deepEqual(readFileSync(paths[1]), bytes);
  assert.equal(readFileSync(paths[2], "utf8"), readFileSync(metadata, "utf8"));
  assert.ok(
    existsSync(
      join(
        dirname(metadata),
        "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz",
      ),
    ),
  );
});

test("verify accepts nested matrix artifacts with different cellar paths", (context) => {
  const dir = temp(context);
  const paths = matrix(dir);
  assert.deepEqual(
    verify({ ...expected, dir: join(dir, "artifacts"), tags }),
    paths,
  );
});

test("verify accepts release-only archive names after download", (context) => {
  const dir = temp(context);
  const paths = matrix(dir);
  for (const [index, path] of paths.entries()) {
    rmSync(
      join(dirname(path), `knowledge-mcp--0.2.0.${tags[index]}.bottle.tar.gz`),
    );
  }
  assert.deepEqual(
    verify({ ...expected, dir: join(dir, "artifacts"), tags }),
    paths,
  );
});

test("stage accepts metadata from the local release tap", (context) => {
  const dir = temp(context);
  const metadata = source(dir);
  change(metadata, (data) => {
    data["local/release/knowledge-mcp"] = data[fullName];
    data["local/release/knowledge-mcp"].formula.path =
      "Library/Taps/local/homebrew-release/Formula/knowledge-mcp.rb";
    delete data[fullName];
  });
  stage({ ...expected, metadata, tag: tags[0], out: join(dir, "out") });
  verify({ ...expected, dir: join(dir, "out"), tags: [tags[0]] });
});

test("stage keeps rebuild suffixes and accepts URL-encoded version metadata", (context) => {
  const dir = temp(context);
  const data = fixture(tags[0], "0.2.0+build_1", 2);
  const metadata = source(join(dir, "source"), data);
  const options = { version: "0.2.0+build_1", rootUrl };
  const paths = stage({
    ...options,
    metadata,
    tag: tags[0],
    out: join(dir, "out"),
  });
  assert.equal(
    paths[0],
    join(
      dir,
      "out",
      "knowledge-mcp-0.2.0+build_1.arm64_sequoia.bottle.2.tar.gz",
    ),
  );
  assert.deepEqual(
    verify({ ...options, dir: join(dir, "out"), tags: [tags[0]] }),
    [paths[2]],
  );
});

test("verify accepts native archive names and checks both names when both are retained", (context) => {
  const dir = temp(context);
  const metadata = source(dir);
  assert.deepEqual(verify({ ...expected, dir, tags: [tags[0]] }), [metadata]);
  const local = join(dir, "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz");
  const remote = join(dir, "knowledge-mcp-0.2.0.arm64_sequoia.bottle.tar.gz");
  copyFileSync(local, remote);
  verify({ ...expected, dir, tags: [tags[0]] });
  writeFileSync(remote, "tampered");
  assert.throws(
    () => verify({ ...expected, dir, tags: [tags[0]] }),
    /SHA-256 mismatch/,
  );
});

const invalidMetadata: Array<[string, (data: Fixture) => void, RegExp]> = [
  [
    "an additional formula",
    (data) => {
      data["other/tap/knowledge-mcp"] = data[fullName];
    },
    /exactly one formula/,
  ],
  [
    "an unqualified formula name",
    (data) => {
      data["knowledge-mcp"] = data[fullName];
      delete data[fullName];
    },
    /fully qualified/,
  ],
  [
    "a different formula name",
    (data) => {
      data[fullName].formula.name = "other";
    },
    /formula.name/,
  ],
  [
    "a different package version",
    (data) => {
      data[fullName].formula.pkg_version = "9.9.9";
    },
    /package version/,
  ],
  [
    "a different root URL",
    (data) => {
      data[fullName].bottle.root_url += "/other";
    },
    /root URL/,
  ],
  [
    "a negative rebuild",
    (data) => {
      data[fullName].bottle.rebuild = -1;
    },
    /rebuild/,
  ],
  [
    "a fractional rebuild",
    (data) => {
      data[fullName].bottle.rebuild = 1.5;
    },
    /rebuild/,
  ],
  [
    "a rebuild above the safe integer limit",
    (data) => {
      data[fullName].bottle.rebuild = Number.MAX_SAFE_INTEGER + 1;
    },
    /rebuild/,
  ],
  [
    "a missing cellar",
    (data) => {
      data[fullName].bottle.cellar = "";
    },
    /cellar/,
  ],
  [
    "multiple tags",
    (data) => {
      data[fullName].bottle.tags.sequoia = data[fullName].bottle.tags[tags[0]];
    },
    /exactly one bottle tag/,
  ],
  [
    "a wrong archive version",
    (data) => {
      data[fullName].bottle.tags[tags[0]].filename =
        "knowledge-mcp-9.9.9.arm64_sequoia.bottle.tar.gz";
    },
    /filename/,
  ],
  [
    "local filename traversal",
    (data) => {
      data[fullName].bottle.tags[tags[0]].local_filename = "../outside.tar.gz";
    },
    /local_filename/,
  ],
  [
    "an encoded path separator",
    (data) => {
      data[fullName].bottle.tags[tags[0]].filename =
        "%2Fknowledge-mcp-0.2.0.arm64_sequoia.bottle.tar.gz";
    },
    /filename/,
  ],
  [
    "double URI encoding",
    (data) => {
      data[fullName].bottle.tags[tags[0]].filename =
        "knowledge-mcp-0%252E2.0.arm64_sequoia.bottle.tar.gz";
    },
    /filename/,
  ],
  [
    "a filename URL",
    (data) => {
      data[fullName].bottle.tags[tags[0]].filename =
        "https://example.com/knowledge-mcp-0.2.0.arm64_sequoia.bottle.tar.gz";
    },
    /filename/,
  ],
  [
    "malformed URI encoding",
    (data) => {
      data[fullName].bottle.tags[tags[0]].filename = "%ZZ";
    },
    /filename/,
  ],
  [
    "a missing hash",
    (data) => {
      data[fullName].bottle.tags[tags[0]].sha256 = "";
    },
    /sha256/,
  ],
  [
    "a nonhex hash",
    (data) => {
      data[fullName].bottle.tags[tags[0]].sha256 = "z".repeat(64);
    },
    /sha256/,
  ],
  [
    "a mismatched formula path",
    (data) => {
      data[fullName].formula.path =
        "Library/Taps/other/homebrew-tap/Formula/knowledge-mcp.rb";
    },
    /formula.path/,
  ],
  [
    "formula path traversal",
    (data) => {
      data[fullName].formula.path =
        "Library/Taps/sterlingjf/homebrew-tap/Formula/../Formula/knowledge-mcp.rb";
    },
    /formula.path/,
  ],
  [
    "a mismatched tap git path",
    (data) => {
      data[fullName].formula.tap_git_path = "Formula/other.rb";
    },
    /tap_git_path/,
  ],
];
for (const [label, mutate, error] of invalidMetadata) {
  test(`stage rejects ${label} before producing artifacts`, (context) => {
    const dir = temp(context);
    const metadata = source(join(dir, "source"));
    change(metadata, mutate);
    const out = join(dir, "out");
    assert.throws(
      () => stage({ ...expected, metadata, tag: tags[0], out }),
      error,
    );
    assert.equal(existsSync(out), false);
  });
}

test("stage rejects malformed JSON and metadata shapes", (context) => {
  const dir = temp(context);
  const metadata = source(dir);
  const valid = JSON.parse(readFileSync(metadata, "utf8")) as Fixture;
  const options = {
    ...expected,
    metadata,
    tag: tags[0],
    out: join(dir, "out"),
  };
  const cases: Array<unknown> = [
    null,
    [],
    {},
    { [fullName]: null },
    { [fullName]: { formula: [], bottle: valid[fullName].bottle } },
    {
      [fullName]: {
        formula: valid[fullName].formula,
        bottle: { ...valid[fullName].bottle, tags: null },
      },
    },
  ];
  for (const data of cases) {
    writeFileSync(metadata, JSON.stringify(data));
    assert.throws(() => stage(options), /object|exactly one formula/);
  }
  writeFileSync(metadata, "{");
  assert.throws(() => stage(options), SyntaxError);
  assert.equal(existsSync(options.out), false);
});

test("stage rejects wrong tag, corrupted bytes and missing source archives", (context) => {
  const dir = temp(context);
  const metadata = source(dir);
  const options = {
    ...expected,
    metadata,
    tag: tags[0],
    out: join(dir, "out"),
  };
  assert.throws(() => stage({ ...options, tag: tags[1] }), /expected tag/);
  const archive = join(dir, "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz");
  writeFileSync(archive, "tampered");
  assert.throws(() => stage(options), /SHA-256 mismatch/);
  rmSync(archive);
  assert.throws(() => stage(options), /ENOENT/);
  assert.equal(existsSync(options.out), false);
});

test("stage does not overwrite an existing output artifact", (context) => {
  const dir = temp(context);
  const metadata = source(join(dir, "source"));
  const options = {
    ...expected,
    metadata,
    tag: tags[0],
    out: join(dir, "out"),
  };
  const paths = stage(options);
  assert.throws(() => stage(options), /EEXIST/);
  assert.deepEqual(readFileSync(paths[0]), bytes);
});

test("verify rejects duplicate, missing and unexpected matrix tags", (context) => {
  const dir = temp(context);
  const paths = matrix(dir);
  const options = { ...expected, dir: join(dir, "artifacts"), tags };
  assert.throws(
    () => verify({ ...options, tags: [tags[0]] }),
    /unexpected bottle tag/,
  );
  assert.throws(
    () => verify({ ...options, tags: [...tags, tags[0]] }),
    /duplicates/,
  );
  const duplicate = join(dirname(paths[0]), "duplicate.bottle.json");
  copyFileSync(paths[0], duplicate);
  assert.throws(() => verify(options), /duplicate bottle tag/);
  rmSync(duplicate);
  rmSync(dirname(paths[1]), { recursive: true });
  assert.throws(() => verify(options), /missing bottle tags: sequoia/);
});

test("verify rejects inconsistent formula names, paths and rebuilds across tags", (context) => {
  const dir = temp(context);
  const paths = matrix(dir);
  const options = { ...expected, dir: join(dir, "artifacts"), tags };
  const original = readFileSync(paths[1], "utf8");
  change(paths[1], (data) => {
    data["another/tap/knowledge-mcp"] = data[fullName];
    data["another/tap/knowledge-mcp"].formula.path =
      "Library/Taps/another/homebrew-tap/Formula/knowledge-mcp.rb";
    delete data[fullName];
  });
  assert.throws(() => verify(options), /inconsistent formula/);
  writeFileSync(paths[1], original);
  change(paths[1], (data) => {
    data[fullName].formula.path =
      "Library/Taps/sterlingjf/homebrew-tap/Formula/k/knowledge-mcp.rb";
    data[fullName].formula.tap_git_path = "Formula/k/knowledge-mcp.rb";
  });
  assert.throws(() => verify(options), /inconsistent formula/);
  writeFileSync(paths[1], original);
  change(paths[1], (data) => {
    data[fullName].bottle.rebuild = 1;
    data[fullName].bottle.tags.sequoia.filename =
      "knowledge-mcp-0.2.0.sequoia.bottle.1.tar.gz";
    data[fullName].bottle.tags.sequoia.local_filename =
      "knowledge-mcp--0.2.0.sequoia.bottle.1.tar.gz";
  });
  assert.throws(() => verify(options), /inconsistent formula/);
});

test("verify rejects corrupt, renamed, orphan and missing archives", (context) => {
  const dir = temp(context);
  const paths = matrix(dir);
  const options = { ...expected, dir: join(dir, "artifacts"), tags };
  const archive = join(
    dirname(paths[0]),
    "knowledge-mcp-0.2.0.arm64_sequoia.bottle.tar.gz",
  );
  writeFileSync(archive, "corrupt");
  assert.throws(() => verify(options), /SHA-256 mismatch/);
  writeFileSync(archive, bytes);
  const wrongName = join(
    dirname(paths[0]),
    "knowledge-mcp-9.9.9.arm64_sequoia.bottle.tar.gz",
  );
  renameSync(archive, wrongName);
  assert.throws(() => verify(options), /unexpected bottle archive filename/);
  renameSync(wrongName, archive);
  const orphan = join(
    options.dir,
    "knowledge-mcp-0.2.0.arm64_sonoma.bottle.tar.gz",
  );
  writeFileSync(orphan, bytes);
  assert.throws(() => verify(options), /unexpected bottle archive filename/);
  rmSync(orphan);
  rmSync(archive);
  rmSync(
    join(dirname(paths[0]), "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz"),
  );
  assert.throws(() => verify(options), /missing bottle archive/);
});

test("stage rejects invalid version and release URL arguments", (context) => {
  const dir = temp(context);
  const metadata = source(dir);
  const options = {
    ...expected,
    metadata,
    tag: tags[0],
    out: join(dir, "out"),
  };
  for (const bad of ["../0.2.0", "0%2F2.0", "", "0.2.0\n"]) {
    assert.throws(
      () => stage({ ...options, version: bad }),
      /safe Homebrew package version/,
    );
  }
  for (const bad of [
    "http://example.com/assets",
    `${rootUrl}/`,
    `${rootUrl}?token=secret`,
    `${rootUrl}#fragment`,
    "https://user:password@example.com/assets",
  ]) {
    assert.throws(() => stage({ ...options, rootUrl: bad }), /root URL/);
  }
});

test("symlinked archives and artifact directories are rejected", (context) => {
  const dir = temp(context);
  const metadata = source(join(dir, "source"));
  const archive = join(
    dirname(metadata),
    "knowledge-mcp--0.2.0.arm64_sequoia.bottle.tar.gz",
  );
  const outside = join(dir, "outside.tar.gz");
  renameSync(archive, outside);
  symlinkSync(outside, archive);
  assert.throws(
    () => stage({ ...expected, metadata, tag: tags[0], out: join(dir, "out") }),
    /ELOOP/,
  );
  assert.throws(
    () => verify({ ...expected, dir: dirname(metadata), tags: [tags[0]] }),
    /symlinks/,
  );
  rmSync(archive);
  writeFileSync(archive, bytes);
  const linkedDir = join(dir, "linked-artifacts");
  symlinkSync(dirname(metadata), linkedDir, "dir");
  assert.throws(
    () => verify({ ...expected, dir: linkedDir, tags: [tags[0]] }),
    /not a regular directory/,
  );
  symlinkSync(dirname(metadata), join(dirname(metadata), "nested-link"), "dir");
  assert.throws(
    () => verify({ ...expected, dir: dirname(metadata), tags: [tags[0]] }),
    /symlinks/,
  );
});

test("the CLI stages and verifies artifacts and rejects invalid command arguments", (context) => {
  const dir = temp(context);
  const metadata = source(join(dir, "source"));
  const out = join(dir, "out");
  const script = fileURLToPath(new URL("./bottle-assets.ts", import.meta.url));
  const run = (...args: Array<string>) =>
    spawnSync(process.execPath, [script, ...args], { encoding: "utf8" });
  const staged = run(
    "stage",
    "--metadata",
    metadata,
    "--version",
    version,
    "--tag",
    tags[0],
    "--root-url",
    rootUrl,
    "--out",
    out,
  );
  assert.equal(staged.status, 0, staged.stderr);
  const checked = run(
    "verify",
    "--dir",
    out,
    "--version",
    version,
    "--root-url",
    rootUrl,
    "--tags",
    tags[0],
  );
  assert.equal(checked.status, 0, checked.stderr);
  assert.match(
    checked.stdout,
    /knowledge-mcp--0.2.0.arm64_sequoia.bottle.json/,
  );
  assert.equal(run("verify", "--dir", out).status, 1);
  assert.equal(run("stage", "--unknown", "value").status, 1);
  assert.equal(
    run(
      "verify",
      "extra",
      "--dir",
      out,
      "--version",
      version,
      "--root-url",
      rootUrl,
      "--tags",
      tags[0],
    ).status,
    1,
  );
});
