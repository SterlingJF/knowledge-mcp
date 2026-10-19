#!/usr/bin/env node

// Keep package and manifest versions aligned with the changelog release.
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { parse } from "smol-toml";
import { format } from "prettier";

export type Run = (
  command: string,
  args: Array<string>,
  options?: { cwd?: string },
) => string;
const jsonFiles = [
  "package.json",
  "runtime/.claude-plugin/plugin.json",
  "runtime/.codex-plugin/plugin.json",
];
function object(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}
function stableVersion(value: unknown): string {
  if (
    typeof value !== "string" ||
    !/^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$/.test(value) ||
    value.split(".").some((part) => !Number.isSafeInteger(Number(part)))
  )
    throw new Error("Use a stable X.Y.Z release version.");
  return value;
}
function packages(root: string): Array<Record<string, unknown>> {
  const lock = parse(readFileSync(join(root, "uv.lock"), "utf8"));
  if (!Array.isArray(lock.package))
    throw new Error("uv.lock packages are missing");
  return lock.package.map((entry) => object(entry, "locked package"));
}
export function validateMetadata(root: string, expected?: string): string {
  const project = object(
    parse(readFileSync(join(root, "runtime/pyproject.toml"), "utf8")).project,
    "runtime project",
  );
  if (project.name !== "knowledge-mcp")
    throw new Error("runtime package name differs");
  const version = stableVersion(project.version);
  if (expected !== undefined && version !== stableVersion(expected))
    throw new Error("release version differs from tagged metadata");
  for (const path of jsonFiles) {
    const metadata = object(
      JSON.parse(readFileSync(join(root, path), "utf8")) as unknown,
      path,
    );
    if (metadata.name !== "knowledge-mcp" || metadata.version !== version)
      throw new Error(`${path} name or version differs from runtime`);
  }
  const own = packages(root).filter((entry) => entry.name === "knowledge-mcp");
  if (
    own.length !== 1 ||
    own[0].version !== version ||
    object(own[0].source, "locked source").editable !== "runtime"
  )
    throw new Error("uv.lock product identity or version differs from runtime");
  return version;
}
interface Entry {
  start: number;
  end: number;
  version: string | undefined;
  pending: boolean;
  body: string;
}
function entries(text: string): Array<Entry> {
  const headings = [...text.matchAll(/^## ([^\r\n]+)\r?$/gm)];
  return headings.map((heading, index) => {
    const title = heading[1].trim();
    const match =
      /^(\d+\.\d+\.\d+)(?:[ \t]+(?:\((unreleased|\d{4}-\d{2}-\d{2})\)|[—–-][ \t]*(unreleased)))?$/i.exec(
        title,
      );
    return {
      start: heading.index,
      end: heading.index + heading[0].length,
      version: match ? stableVersion(match[1]) : undefined,
      pending:
        /^unreleased$/i.test(title) ||
        Boolean(
          match && /^unreleased$/i.test(match.at(2) ?? match.at(3) ?? ""),
        ),
      body: text
        .slice(heading.index + heading[0].length, headings[index + 1]?.index)
        .trim(),
    };
  });
}
export function releaseNotes(root: string, version: string): string {
  stableVersion(version);
  const matching = entries(
    readFileSync(join(root, "CHANGELOG.md"), "utf8"),
  ).filter((entry) => entry.version === version);
  if (matching.length !== 1 || matching[0].pending)
    throw new Error(
      `CHANGELOG.md needs one completed release notes entry for ${version}.`,
    );
  const body = matching[0].body;
  if (!/^- \S/m.test(body) || /\b(?:TODO|TBD)\b/i.test(body))
    throw new Error(
      "Finish release notes: include changes and resolve TODO/TBD placeholders.",
    );
  return body;
}
const execute: Run = (command, args, options) => {
  const result = spawnSync(command, args, {
    cwd: options?.cwd,
    encoding: "utf8",
  });
  if (result.error) throw result.error;
  if (result.status !== 0)
    throw new Error(`${command} failed: ${result.stderr || result.stdout}`);
  return result.stdout.trim();
};

export async function prepare(
  root: string,
  version: string,
  run: Run = execute,
): Promise<void> {
  stableVersion(version);
  const current = validateMetadata(root);
  const nextParts = version.split(".").map(Number);
  const currentParts = current.split(".").map(Number);
  const difference = nextParts.findIndex(
    (part, index) => part !== currentParts[index],
  );
  if (difference < 0 || nextParts[difference] < currentParts[difference])
    throw new Error(`Choose a release version greater than ${current}.`);
  if (run("git", ["tag", "--list", `v${version}`], { cwd: root }).trim())
    throw new Error(`Tag v${version} already exists.`);
  const changelog = readFileSync(join(root, "CHANGELOG.md"), "utf8");
  const sections = entries(changelog);
  if (sections.some((entry) => entry.version === version && !entry.pending))
    throw new Error(`Release ${version} already has a changelog entry.`);
  const pending = sections.filter(
    (entry) =>
      entry.pending &&
      (entry.version === version || entry.version === undefined),
  );
  if (pending.length > 1)
    throw new Error(
      "Keep one pending changelog entry for the release; duplicate entries were found.",
    );
  const ownFiles = [
    "runtime/pyproject.toml",
    ...jsonFiles,
    "CHANGELOG.md",
    "uv.lock",
    "runtime/requirements.lock",
    "pnpm-lock.yaml",
  ];
  const original = new Map(
    ownFiles.map((path) => [path, readFileSync(join(root, path))]),
  );
  const originalPackages = packages(root);
  try {
    const path = join(root, "runtime/pyproject.toml");
    const text = readFileSync(path, "utf8");
    const section =
      /^\[project\][ \t]*\r?\n([\s\S]*?)(?=^\[|$(?![\s\S]))/m.exec(text);
    if (!section)
      throw new Error("runtime/pyproject.toml needs a static project section.");
    let replacements = 0;
    const updated = section[1].replace(
      /^([ \t]*version[ \t]*=[ \t]*)(["'])[^"']*\2([ \t]*(?:#.*)?)$/gm,
      (_match, prefix: string, quote: string, suffix: string) => {
        replacements++;
        return `${prefix}${quote}${version}${quote}${suffix}`;
      },
    );
    if (replacements !== 1)
      throw new Error(
        "runtime/pyproject.toml needs one static project.version.",
      );
    writeFileSync(
      path,
      text.replace(section[0], section[0].replace(section[1], updated)),
    );
    for (const file of jsonFiles) {
      const metadata = object(
        JSON.parse(readFileSync(join(root, file), "utf8")) as unknown,
        file,
      );
      metadata.version = version;
      writeFileSync(
        join(root, file),
        await format(JSON.stringify(metadata), { filepath: join(root, file) }),
      );
    }
    const heading = pending.at(0);
    const prepared = heading
      ? changelog.slice(0, heading.start) +
        `## ${version}` +
        changelog.slice(heading.end)
      : (() => {
          const offset = sections[0]?.start ?? changelog.length;
          return (
            changelog.slice(0, offset) +
            `## ${version}\n\n### Changes\n\n- TODO: Describe the user-facing changes.\n\n` +
            changelog.slice(offset)
          );
        })();
    writeFileSync(join(root, "CHANGELOG.md"), prepared);
    run("uv", ["lock"], { cwd: root });
    const updatedPackages = packages(root).map((entry) =>
      entry.name === "knowledge-mcp" ? { ...entry, version: current } : entry,
    );
    if (JSON.stringify(updatedPackages) !== JSON.stringify(originalPackages))
      throw new Error(
        "Release preparation changed unrelated dependency pins in uv.lock.",
      );
    run("just", ["generate_knowledge_mcp_lock"], { cwd: root });
    validateMetadata(root, version);
    if (
      !readFileSync(join(root, "pnpm-lock.yaml")).equals(
        original.get("pnpm-lock.yaml")!,
      )
    )
      throw new Error("Release preparation changed the pnpm dependency lock.");
  } catch (error) {
    for (const [file, bytes] of original)
      writeFileSync(join(root, file), bytes);
    throw error;
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const { values, positionals } = parseArgs({
      allowPositionals: true,
      options: {
        version: { type: "string" },
        root: { type: "string", default: "." },
      },
    });
    const root = resolve(values.root);
    if (positionals.length !== 1)
      throw new Error("Use release-metadata prepare or check.");
    if (positionals[0] === "prepare") {
      if (!values.version) throw new Error("prepare requires --version X.Y.Z");
      await prepare(root, values.version);
      console.log(
        `Prepared release ${values.version}. Review CHANGELOG.md, then run just release_check.`,
      );
    } else if (positionals[0] === "check") {
      const version = validateMetadata(root);
      releaseNotes(root, version);
      console.log(`Release ${version} metadata and notes are valid.`);
    } else throw new Error("Use release-metadata prepare or check.");
  } catch (error) {
    console.error(
      error instanceof Error ? error.message : "Release preparation failed",
    );
    process.exitCode = 1;
  }
}
