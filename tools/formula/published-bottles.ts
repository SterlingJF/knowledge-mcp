#!/usr/bin/env node

// Publish and restore bottle metadata with its archive.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  appendFileSync,
  closeSync,
  constants,
  copyFileSync,
  fstatSync,
  mkdtempSync,
  openSync,
  readSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { readMetadata, stage, verify } from "./bottle-assets.ts";

export interface Options {
  version: string;
  tag: string;
  rootUrl: string;
}
interface Release {
  version: string;
  rootUrl: string;
  repo: string;
  releaseTag: string;
}
export type Run = (args: Array<string>) => string;
const runGh: Run = (args) => {
  try {
    return execFileSync("gh", args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch {
    throw new Error(`gh release ${args[1]} failed`);
  }
};

function names(options: Options) {
  if (
    !/^[A-Za-z0-9][A-Za-z0-9._+-]*$/.test(options.version) ||
    !/^[a-z][a-z0-9_]*$/.test(options.tag)
  )
    throw new Error("invalid bottle version or tag");
  const base = `knowledge-mcp--${options.version}.${options.tag}`;
  return {
    json: `${base}.bottle.json`,
    local: `${base}.bottle.tar.gz`,
    remote: `knowledge-mcp-${options.version}.${options.tag}.bottle.tar.gz`,
  };
}

function inventory(options: Release, run: Run): Set<string> {
  if (
    !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(options.repo) ||
    options.releaseTag !== `v${options.version}` ||
    options.rootUrl !==
      `https://github.com/${options.repo}/releases/download/${options.releaseTag}`
  )
    throw new Error("release identity differs from bottle root URL/version");
  const value: unknown = JSON.parse(
    run([
      "release",
      "view",
      options.releaseTag,
      "--repo",
      options.repo,
      "--json",
      "assets",
    ]),
  );
  if (
    value === null ||
    typeof value !== "object" ||
    !("assets" in value) ||
    !Array.isArray(value.assets)
  )
    throw new Error("invalid release asset inventory");
  const assets: Array<string> = [];
  for (const asset of value.assets as Array<unknown>) {
    if (
      asset === null ||
      typeof asset !== "object" ||
      !("name" in asset) ||
      typeof asset.name !== "string"
    )
      throw new Error("invalid release asset name");
    assets.push(asset.name);
  }
  if (new Set(assets).size !== assets.length)
    throw new Error("duplicate release assets");
  return new Set(assets);
}

function digest(path: string): string {
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    if (!fstatSync(fd).isFile())
      throw new Error("release assets must be regular files");
    const hash = createHash("sha256");
    const buffer = Buffer.alloc(1024 * 1024);
    let count: number;
    while ((count = readSync(fd, buffer)) > 0)
      hash.update(buffer.subarray(0, count));
    return hash.digest("hex");
  } finally {
    closeSync(fd);
  }
}

function download(options: Release, name: string, dir: string, run: Run) {
  run([
    "release",
    "download",
    options.releaseTag,
    "--repo",
    options.repo,
    "--pattern",
    name,
    "--dir",
    dir,
  ]);
}

export function restore(
  options: Release & { tag: string; out: string },
  run: Run = runGh,
): boolean {
  const expected = names(options);
  const assets = inventory(options, run);
  const hasJson = assets.has(expected.json);
  const hasArchive = assets.has(expected.remote);
  if (!hasJson && !hasArchive) return false;
  if (!hasJson || !hasArchive)
    throw new Error(
      "Incomplete published bottle pair: rerun failed jobs to reuse retained Actions artifacts; do not rebuild or overwrite assets.",
    );
  const scratch = mkdtempSync(join(tmpdir(), "bottle-pair-"));
  try {
    download(options, expected.json, scratch, run);
    download(options, expected.remote, scratch, run);
    const metadata = readMetadata(join(scratch, expected.json), options);
    if (
      metadata.localName !== expected.local ||
      metadata.remoteName !== expected.remote ||
      metadata.tag !== options.tag
    )
      throw new Error("published metadata differs from expected bottle");
    copyFileSync(
      join(scratch, expected.remote),
      join(scratch, metadata.localName),
      constants.COPYFILE_EXCL,
    );
    stage({ ...options, metadata: join(scratch, expected.json) });
    return true;
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
}

export function publish(
  options: Release & { dir: string; tags: Array<string> },
  run: Run = runGh,
): void {
  const files = verify(options);
  const records = files.map((path) => {
    const metadata = readMetadata(path, options);
    const expected = names({ ...options, tag: metadata.tag });
    if (
      basename(path) !== expected.json ||
      metadata.remoteName !== expected.remote ||
      metadata.localName !== expected.local
    )
      throw new Error(
        "release requires original rebuild-zero native filenames",
      );
    const archive = join(dirname(path), metadata.remoteName);
    return {
      json: path,
      jsonHash: digest(path),
      archive,
      archiveHash: metadata.sha256,
    };
  });
  const assets = inventory(options, run);
  function attach(path: string, expectedHash: string) {
    const name = basename(path);
    if (!assets.has(name)) {
      run([
        "release",
        "upload",
        options.releaseTag,
        path,
        "--repo",
        options.repo,
      ]);
      assets.add(name);
    }
    const scratch = mkdtempSync(join(tmpdir(), "bottle-published-"));
    try {
      download(options, name, scratch, run);
      if (digest(join(scratch, name)) !== expectedHash)
        throw new Error(
          `Published asset differs: ${name}; existing assets are never overwritten`,
        );
    } finally {
      rmSync(scratch, { recursive: true, force: true });
    }
  }
  for (const record of records) attach(record.json, record.jsonHash);
  for (const record of records) attach(record.archive, record.archiveHash);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const { values, positionals } = parseArgs({
      allowPositionals: true,
      options: {
        version: { type: "string" },
        tag: { type: "string" },
        "root-url": { type: "string" },
        repo: { type: "string" },
        "release-tag": { type: "string" },
        out: { type: "string" },
        dir: { type: "string" },
        tags: { type: "string" },
      },
    });
    if (
      positionals.length !== 1 ||
      !values.version ||
      !values["root-url"] ||
      !values.repo ||
      !values["release-tag"]
    )
      throw new Error(
        "Usage: published-bottles restore|publish --version --root-url --repo --release-tag",
      );
    const release = {
      version: values.version,
      rootUrl: values["root-url"],
      repo: values.repo,
      releaseTag: values["release-tag"],
    };
    if (
      positionals[0] === "restore" &&
      values.tag &&
      values.out &&
      !values.dir &&
      !values.tags
    ) {
      const restored = restore({
        ...release,
        tag: values.tag,
        out: values.out,
      });
      if (process.env.GITHUB_OUTPUT)
        appendFileSync(process.env.GITHUB_OUTPUT, `restored=${restored}\n`);
      console.log(`restored=${restored}`);
    } else if (
      positionals[0] === "publish" &&
      values.dir &&
      values.tags &&
      !values.out &&
      !values.tag
    ) {
      publish({ ...release, dir: values.dir, tags: values.tags.split(",") });
      console.log("Native bottle metadata and archives verified.");
    } else throw new Error("invalid restore/publish arguments");
  } catch (error) {
    console.error(
      error instanceof Error ? error.message : "Bottle publication failed",
    );
    process.exitCode = 1;
  }
}
