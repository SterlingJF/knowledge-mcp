#!/usr/bin/env node

// Root release recipes share this policy; Homebrew owns bottle mechanics.
import { spawnSync } from "node:child_process";
import {
  appendFileSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { stage } from "./bottle-assets.ts";
import { measureInstall } from "./install-report.ts";
import type { Runner } from "./install-report.ts";
import { publish, restore } from "./published-bottles.ts";

export type { Runner } from "./install-report.ts";

export interface Release {
  tag: string;
  version: string;
  commit: string;
  repo: string;
  rootUrl: string;
}
interface StageOptions {
  release: Release;
  root: string;
}
interface NativeOptions extends StageOptions {
  arch: string;
  prefix: string;
  bottleTag: string;
}
const tags = ["arm64_sequoia", "sequoia"];
const formulaName = "local/release/knowledge-mcp";

export class CommandError extends Error {
  httpStatus: number | undefined;
  constructor(command: string, operation: string, stdout: string) {
    super(`${command} ${operation} failed`);
    this.httpStatus =
      command === "gh" && operation === "api"
        ? responseStatus(stdout)
        : undefined;
  }
}

function responseStatus(response: string): number | undefined {
  const status = /^HTTP\/\S+ (\d{3})(?:\s|$)/m.exec(response)?.[1];
  return status === undefined ? undefined : Number(status);
}

const execute: Runner = (command, args, options) => {
  const result = spawnSync(command, args, {
    cwd: options?.cwd,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.error) throw result.error;
  if (options?.log) {
    writeFileSync(options.log, result.stdout + result.stderr);
    process.stdout.write(result.stdout);
    process.stderr.write(result.stderr);
  }
  if (result.status !== 0)
    throw new CommandError(command, args.at(0) ?? "", result.stdout);
  return result.stdout.trim();
};

function object(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}

function stableVersion(value: string): Array<number> {
  if (!/^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/.test(value))
    throw new Error("release requires a stable X.Y.Z version");
  return value.split(".").map(Number);
}

function validateRelease(release: Release) {
  stableVersion(release.version);
  if (
    release.tag !== `v${release.version}` ||
    !/^[a-f0-9]{40}$/.test(release.commit) ||
    !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(release.repo) ||
    release.rootUrl !==
      `https://github.com/${release.repo}/releases/download/${release.tag}`
  )
    throw new Error("invalid release identity");
}

async function packageVersion(text: string): Promise<string> {
  const { parse } = await import("smol-toml");
  const project = object(parse(text).project, "project");
  if (typeof project.version !== "string")
    throw new Error("package version is missing");
  return project.version;
}

export async function target(
  options: { tag: string; repo: string; root: string },
  run: Runner = execute,
): Promise<Release> {
  if (!options.tag.startsWith("v")) throw new Error("invalid release tag");
  stableVersion(options.tag.slice(1));
  const commit = run(
    "git",
    ["rev-parse", "--verify", `refs/tags/${options.tag}^{commit}`],
    { cwd: options.root },
  ).trim();
  const manifest = run("git", ["show", `${commit}:runtime/pyproject.toml`], {
    cwd: options.root,
  });
  const version = await packageVersion(manifest);
  if (options.tag !== `v${version}`)
    throw new Error("tag differs from package version");
  const release = {
    tag: options.tag,
    version,
    commit,
    repo: options.repo,
    rootUrl: `https://github.com/${options.repo}/releases/download/${options.tag}`,
  };
  validateRelease(release);
  mkdirSync(join(options.root, "dist"), { recursive: true });
  writeFileSync(
    join(options.root, "dist/release.json"),
    `${JSON.stringify(release, null, 2)}\n`,
  );
  return release;
}

function releaseAssets(release: Release, run: Runner): Set<string> {
  const responseText = run("gh", [
    "api",
    "--include",
    `repos/${release.repo}/releases/tags/${release.tag}`,
  ]);
  const separator = /\r?\n\r?\n/.exec(responseText);
  if (responseStatus(responseText) !== 200 || !separator)
    throw new Error("invalid GitHub release API response");
  const response = object(
    JSON.parse(
      responseText.slice(separator.index + separator[0].length),
    ) as unknown,
    "release inventory",
  );
  if (!Array.isArray(response.assets))
    throw new Error("release inventory assets are missing");
  const assets = new Set<string>();
  for (const entry of response.assets as Array<unknown>) {
    const asset = object(entry, "release asset");
    if (typeof asset.name !== "string" || assets.has(asset.name))
      throw new Error("invalid or duplicate release asset name");
    assets.add(asset.name);
  }
  return assets;
}

export async function source(
  options: StageOptions & { source: string },
  run: Runner = execute,
): Promise<void> {
  validateRelease(options.release);
  const checkout = resolve(options.source);
  if (
    run("git", ["rev-parse", "HEAD"], { cwd: checkout }).trim() !==
    options.release.commit
  )
    throw new Error("source checkout differs from released tag commit");
  if (
    run("git", ["status", "--porcelain", "--untracked-files=normal"], {
      cwd: checkout,
    }).trim()
  )
    throw new Error("source checkout must be clean to match the released tag");
  const manifest = readFileSync(
    join(checkout, "runtime/pyproject.toml"),
    "utf8",
  );
  if ((await packageVersion(manifest)) !== options.release.version)
    throw new Error("source checkout differs from released package version");
  const { validateMetadata, releaseNotes } =
    await import("./release-metadata.ts");
  validateMetadata(checkout, options.release.version);
  run("just", ["check_knowledge_mcp_lock", checkout], { cwd: options.root });
  const dist = join(options.root, "dist");
  mkdirSync(dist, { recursive: true });
  let assets: Set<string>;
  let releaseMissing = false;
  try {
    assets = releaseAssets(options.release, run);
  } catch (error) {
    if (
      !(error instanceof Error) ||
      !("httpStatus" in error) ||
      error.httpStatus !== 404
    )
      throw error;
    releaseMissing = true;
    assets = new Set();
  }
  const name = `knowledge_mcp-${options.release.version}.tar.gz`;
  const archive = join(dist, name);
  const newSource = !assets.has(name);
  const notes = newSource
    ? releaseNotes(checkout, options.release.version)
    : "";
  if (!newSource)
    run("gh", [
      "release",
      "download",
      options.release.tag,
      "--repo",
      options.release.repo,
      "--pattern",
      name,
      "--dir",
      dist,
    ]);
  else
    run("just", ["build_knowledge_mcp", checkout, dist], { cwd: options.root });
  const identity = run("tar", [
    "--extract",
    "--to-stdout",
    "--file",
    archive,
    `knowledge_mcp-${options.release.version}/PKG-INFO`,
  ]);
  const nameField = /^Name: (.+)$/m.exec(identity)?.[1];
  const versionField = /^Version: (.+)$/m.exec(identity)?.[1];
  if (
    nameField?.replace(/_/g, "-") !== "knowledge-mcp" ||
    versionField !== options.release.version
  )
    throw new Error(
      "source archive package identity differs from released tag",
    );
  const { generate } = await import("./generate-formula.ts");
  const formula = generate({
    sdist: readFileSync(archive),
    url: `${options.release.rootUrl}/${name}`,
    lock: readFileSync(join(checkout, "uv.lock"), "utf8"),
    requirements: readFileSync(
      join(checkout, "runtime/requirements.lock"),
      "utf8",
    ),
    pyproject: manifest,
  });
  if (newSource) {
    if (releaseMissing) {
      const notesPath = join(dist, "release-notes.md");
      writeFileSync(notesPath, `${notes}\n`);
      run("gh", [
        "release",
        "create",
        options.release.tag,
        "--repo",
        options.release.repo,
        "--verify-tag",
        "--title",
        options.release.tag,
        "--notes-file",
        notesPath,
      ]);
    }
    run("gh", [
      "release",
      "upload",
      options.release.tag,
      archive,
      "--repo",
      options.release.repo,
    ]);
  }
  writeFileSync(join(dist, "knowledge-mcp.rb"), formula);
  writeFileSync(
    join(dist, "release.json"),
    `${JSON.stringify(options.release, null, 2)}\n`,
  );
}

function nativeHost(options: NativeOptions, run: Runner) {
  const expected =
    options.arch === "arm64"
      ? { prefix: "/opt/homebrew", tag: "arm64_sequoia" }
      : options.arch === "x86_64"
        ? { prefix: "/usr/local", tag: "sequoia" }
        : undefined;
  if (
    !expected ||
    options.prefix !== expected.prefix ||
    options.bottleTag !== expected.tag
  )
    throw new Error("invalid native bottle target");
  if (
    run("uname", ["-m"]).trim() !== options.arch ||
    run("sw_vers", ["-productVersion"]).trim().split(".")[0] !== "15" ||
    run("brew", ["--prefix"]).trim() !== options.prefix
  )
    throw new Error("runner differs from native Sequoia bottle target");
}

function localTap(
  root: string,
  run: Runner,
  name = "local/release",
  sourcePath = join(root, "dist/knowledge-mcp.rb"),
): string {
  const path = tapFile(name, run);
  copyFileSync(sourcePath, path);
  run("brew", ["trust", "--formula", `${name}/knowledge-mcp`], {
    log: join(root, "dist/formula-trust.log"),
  });
  return path;
}

function tapFile(name: string, run: Runner): string {
  const repository = run("brew", ["--repository", name]).trim();
  if (!existsSync(repository)) run("brew", ["tap-new", "--no-git", name]);
  return join(repository, "Formula/knowledge-mcp.rb");
}

function pairRelease(release: Release) {
  return {
    version: release.version,
    rootUrl: release.rootUrl,
    repo: release.repo,
    releaseTag: release.tag,
  };
}

export function bottle(options: NativeOptions, run: Runner = execute): void {
  validateRelease(options.release);
  nativeHost(options, run);
  const out = join(options.root, "bottles");
  if (
    restore(
      { ...pairRelease(options.release), tag: options.bottleTag, out },
      (args) => run("gh", args),
    )
  )
    return;
  localTap(options.root, run);
  run("brew", ["style", formulaName]);
  run("brew", ["install", "--build-bottle", formulaName]);
  run("brew", ["test", formulaName]);
  run("brew", ["linkage", "--test", formulaName]);
  const build = join(options.root, "bottle-build");
  mkdirSync(build, { recursive: true });
  run(
    "brew",
    [
      "bottle",
      "--json",
      "--no-rebuild",
      `--root-url=${options.release.rootUrl}`,
      formulaName,
    ],
    { cwd: build },
  );
  stage({
    version: options.release.version,
    rootUrl: options.release.rootUrl,
    tag: options.bottleTag,
    metadata: join(
      build,
      `knowledge-mcp--${options.release.version}.${options.bottleTag}.bottle.json`,
    ),
    out,
  });
}

export function merge(options: StageOptions, run: Runner = execute): void {
  validateRelease(options.release);
  const dir = join(options.root, "bottles");
  publish({ ...pairRelease(options.release), dir, tags }, (args) =>
    run("gh", args),
  );
  const formula = localTap(options.root, run);
  run(
    "brew",
    [
      "bottle",
      "--merge",
      "--write",
      "--no-commit",
      "--no-all-checks",
      ...tags.map((tag) =>
        join(
          dir,
          `knowledge-mcp--${options.release.version}.${tag}.bottle.json`,
        ),
      ),
    ],
    { cwd: dir, log: join(dir, "merge.log") },
  );
  run("brew", ["style", formulaName]);
  copyFileSync(formula, join(options.root, "dist/knowledge-mcp.rb"));
}

export function verifyInstalls(
  options: NativeOptions,
  run: Runner = execute,
): void {
  validateRelease(options.release);
  nativeHost(options, run);
  localTap(options.root, run);
  run("brew", ["audit", "--strict", formulaName]);
  for (const dependency of run("brew", [
    "deps",
    "--include-build",
    "--formula",
    formulaName,
  ])
    .trim()
    .split("\n")
    .filter(Boolean))
    run("brew", ["install", dependency]);
  const reports = join(options.root, "install-reports");
  mkdirSync(reports, { recursive: true });
  const installed = object(
    JSON.parse(run("brew", ["info", "--json=v2", formulaName])) as unknown,
    "installed formula response",
  );
  if (!Array.isArray(installed.formulae) || installed.formulae.length !== 1)
    throw new Error("expected one formula before timed installs");
  const existing = object(installed.formulae[0], "installed formula");
  if (!Array.isArray(existing.installed))
    throw new Error("installed formula state is missing");
  if (existing.installed.length > 0) run("brew", ["uninstall", formulaName]);
  const measured = [];
  for (const kind of ["source", "bottle"] as const) {
    for (const flag of ["--build-from-source", "--force-bottle"])
      rmSync(run("brew", ["--cache", flag, formulaName]).trim(), {
        force: true,
      });
    measured.push(
      measureInstall(
        {
          formula: formulaName,
          version: options.release.version,
          kind,
          tag: options.bottleTag,
          commit: options.release.commit,
          out: join(reports, `${kind}-install.json`),
        },
        run,
      ),
    );
    run("brew", ["test", formulaName], {
      log: join(reports, `${kind}-test.log`),
    });
    run("brew", ["linkage", "--test", formulaName], {
      log: join(reports, `${kind}-linkage.log`),
    });
    run(
      join(run("brew", ["--prefix", formulaName]).trim(), "bin/kb"),
      ["doctor"],
      { log: join(reports, `${kind}-doctor.log`) },
    );
    run("brew", ["uninstall", formulaName]);
  }
  const sourceReport = measured.at(0);
  const bottleReport = measured.at(1);
  if (process.env.GITHUB_STEP_SUMMARY && sourceReport && bottleReport)
    appendFileSync(
      process.env.GITHUB_STEP_SUMMARY,
      `## ${options.bottleTag} installation\n\nRuntime and build dependencies were preinstalled; target downloads were cleared. These measurements exclude cold dependency setup.\n\n| Source | Bottle |\n| --- | --- |\n| ${sourceReport.elapsed_seconds.toFixed(3)}s | ${bottleReport.elapsed_seconds.toFixed(3)}s |\n`,
    );
}

function formulaInfo(name: string, run: Runner) {
  const value = object(
    JSON.parse(
      run("brew", ["info", "--json=v2", "--formula", name]),
    ) as unknown,
    "formula response",
  );
  if (!Array.isArray(value.formulae) || value.formulae.length !== 1)
    throw new Error("expected one knowledge-mcp formula");
  const formula = object(value.formulae[0], "formula");
  const versions = object(formula.versions, "formula versions");
  const stable = object(
    object(formula.urls, "formula URLs").stable,
    "stable source",
  );
  if (
    formula.name !== "knowledge-mcp" ||
    typeof versions.stable !== "string" ||
    typeof formula.revision !== "number" ||
    typeof stable.url !== "string" ||
    typeof stable.checksum !== "string"
  )
    throw new Error("invalid knowledge-mcp formula data");
  return {
    version: versions.stable,
    revision: formula.revision,
    url: stable.url,
    checksum: stable.checksum,
  };
}

export function tap(
  options: StageOptions & { tap: string },
  run: Runner = execute,
): void {
  validateRelease(options.release);
  localTap(options.root, run, "local/candidate");
  const candidate = formulaInfo("local/candidate/knowledge-mcp", run);
  if (candidate.version !== options.release.version)
    throw new Error("candidate differs from released version");
  const path = join(options.tap, "Formula/knowledge-mcp.rb");
  if (existsSync(path)) {
    localTap(options.root, run, "local/current", path);
    const current = formulaInfo("local/current/knowledge-mcp", run);
    const currentParts = stableVersion(current.version);
    const candidateParts = stableVersion(candidate.version);
    const firstDifference = currentParts.findIndex(
      (part, index) => part !== candidateParts[index],
    );
    if (
      firstDifference >= 0 &&
      currentParts[firstDifference] > candidateParts[firstDifference]
    )
      throw new Error("refuse to downgrade the tap");
    if (current.version === candidate.version) {
      if (current.revision !== candidate.revision)
        throw new Error("same-version update must preserve formula revision");
      if (current.url !== candidate.url)
        throw new Error("same-version update must preserve source URL");
      if (current.checksum !== candidate.checksum)
        throw new Error("same-version update must preserve source checksum");
    }
  }
  copyFileSync(join(options.root, "dist/knowledge-mcp.rb"), path);
  const cwd = { cwd: options.tap };
  run("git", ["config", "user.name", "github-actions[bot]"], cwd);
  run(
    "git",
    [
      "config",
      "user.email",
      "41898282+github-actions[bot]@users.noreply.github.com",
    ],
    cwd,
  );
  run("git", ["add", "Formula/knowledge-mcp.rb"], cwd);
  if (!run("git", ["diff", "--cached", "--name-only"], cwd).trim()) return;
  run(
    "git",
    [
      "commit",
      "-m",
      `knowledge-mcp ${options.release.version}: native macOS bottles`,
    ],
    cwd,
  );
  run("git", ["push"], cwd);
}

function readRelease(path: string): Release {
  const value = object(
    JSON.parse(readFileSync(path, "utf8")) as unknown,
    "release manifest",
  );
  for (const key of ["tag", "version", "commit", "repo", "rootUrl"])
    if (typeof value[key] !== "string")
      throw new Error(`release manifest ${key} is missing`);
  const release = value as unknown as Release;
  validateRelease(release);
  return release;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const { values, positionals } = parseArgs({
      allowPositionals: true,
      options: {
        tag: { type: "string" },
        repo: { type: "string" },
        release: { type: "string" },
        source: { type: "string" },
        arch: { type: "string" },
        prefix: { type: "string" },
        "bottle-tag": { type: "string" },
        tap: { type: "string" },
      },
    });
    if (
      positionals.length !== 1 ||
      !["target", "source", "bottle", "merge", "verify", "tap"].includes(
        positionals[0],
      )
    )
      throw new Error(
        "Usage: release target|source|bottle|merge|verify|tap with required stage flags",
      );
    const stageName = positionals[0];
    const root = process.cwd();
    if (stageName === "target") {
      if (!values.tag || !values.repo)
        throw new Error("target requires tag and repo");
      const release = await target({
        tag: values.tag,
        repo: values.repo,
        root,
      });
      if (process.env.GITHUB_OUTPUT)
        appendFileSync(
          process.env.GITHUB_OUTPUT,
          `tag=${release.tag}\nversion=${release.version}\ncommit=${release.commit}\nroot_url=${release.rootUrl}\n`,
        );
    } else {
      if (!values.release) throw new Error("stage requires release manifest");
      const options = { release: readRelease(values.release), root };
      if (stageName === "source") {
        if (!values.source)
          throw new Error("source stage requires source checkout");
        await source({ ...options, source: values.source });
      } else if (stageName === "merge") merge(options);
      else if (stageName === "tap") {
        if (!values.tap) throw new Error("tap stage requires tap checkout");
        tap({ ...options, tap: values.tap });
      } else {
        if (!values.arch || !values.prefix || !values["bottle-tag"])
          throw new Error("native stage requires arch, prefix and bottle-tag");
        const native = {
          ...options,
          arch: values.arch,
          prefix: values.prefix,
          bottleTag: values["bottle-tag"],
        };
        if (stageName === "bottle") bottle(native);
        else verifyInstalls(native);
      }
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : "Release failed");
    process.exitCode = 1;
  }
}
