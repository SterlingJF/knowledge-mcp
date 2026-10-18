#!/usr/bin/env node

// Checks the archive before replacing files to preserve the current copy on validation errors.

import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";
import { gunzipSync } from "node:zlib";

import { format } from "prettier";

const repository = "SterlingJF/knowledge-bus";
const defaultSource = `https://codeload.github.com/${repository}/tar.gz`;
const copied = ["universes", "skills"] as const;
type Area = (typeof copied)[number];

/** Relative to the plugin folder. */
const destination: Record<Area, string> = {
  universes: "knowledge-bus/universes",
  skills: "skills",
};
const notesPath = "knowledge-bus/UPSTREAM.md";
const ownSkill =
  /^(?:kb-write-document|kb-track-document-types|kb-import-document)$/;

const usage =
  "Usage: node tools/knowledge-model/refresh-knowledge-model.ts --ref <tag> [--plugin <dir>] [--source <url-or-dir>]\n" +
  "       node tools/knowledge-model/refresh-knowledge-model.ts --check [--plugin <dir>]";

interface Entry {
  path: string;
  mode: number;
  data: Buffer;
}

interface Options {
  /** Empty with --check. */
  ref: string;
  check: boolean;
  /** Absolute path. */
  plugin: string;
  /** The plugin folder as given, for messages. */
  shown: string;
  source: string;
}

const options = readArgs();
if (options.check) {
  check();
} else {
  await refresh();
}

async function refresh(): Promise<void> {
  const pin = readPin();
  if (pin !== options.ref) {
    fail(
      `The ref ${options.ref} differs from the knowledge-bus pin ${pin} in ${join(options.plugin, "pyproject.toml")}. ` +
        "Change the pin and run uv lock first, so the knowledge-bus package and the copied files come from one release.",
    );
  }
  const entries = select(untar(gunzipSync(await read())));
  const folders: Record<Area, Array<string>> = {
    universes: foldersOf(entries, "universes"),
    skills: foldersOf(entries, "skills"),
  };
  for (const area of copied) {
    if (folders[area].length === 0)
      fail(`The archive has no folders under ${area}/.`);
  }
  for (const folder of folders.skills.filter((name) => ownSkill.test(name))) {
    fail(
      `Upstream skill skills/${folder}/ has the same name as a knowledge-mcp skill. Rename the upstream skill.`,
    );
  }
  const notes = await upstreamNotes(entries, folders);
  install(entries, folders, notes);
  for (const area of copied) {
    for (const folder of folders[area]) {
      console.log(
        `wrote: ${destination[area]}/${folder}/ <- ${area}/${folder}/@${options.ref}`,
      );
    }
  }
  console.log(`wrote: ${notesPath}`);
}

function readArgs(): Options {
  try {
    const { values } = parseArgs({
      options: {
        ref: { type: "string" },
        check: { type: "boolean", default: false },
        plugin: { type: "string", default: "runtime" },
        source: { type: "string", default: defaultSource },
      },
      strict: true,
    });
    const ref = values.ref ?? "";
    if (values.check === (ref !== "")) fail(usage);
    if (
      !values.check &&
      (!/^[\w.-]+(?:\/[\w.-]+)*$/.test(ref) || /(^|\/)\.\.?(\/|$)/.test(ref))
    ) {
      fail(`Not a ref: ${ref}`);
    }
    return {
      ref,
      check: values.check,
      plugin: resolve(values.plugin),
      shown: values.plugin,
      source: values.source.replace(/\/+$/, ""),
    };
  } catch {
    return fail(usage);
  }
}

function reason(error: unknown): string {
  if (error instanceof Error) {
    return "code" in error && typeof error.code === "string"
      ? error.code
      : error.message;
  }
  return String(error);
}

/** Fails when pyproject.toml in the plugin folder lacks a knowledge-bus release archive pin. */
function readPin(): string {
  const path = join(options.plugin, "pyproject.toml");
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (error) {
    return fail(`${path}: ${reason(error)}`);
  }
  const match =
    /knowledge-bus\s*@\s*https:\/\/github\.com\/SterlingJF\/knowledge-bus\/releases\/download\/([^/"\s]+)\/knowledge_bus-[^/"\s]+\.tar\.gz/.exec(
      text,
    );
  if (!match) {
    return fail(
      `${path} has no knowledge-bus pin to a release archive (https://github.com/${repository}/releases/download/<tag>/knowledge_bus-<version>.tar.gz).`,
    );
  }
  return match[1];
}

async function read(): Promise<Buffer> {
  if (/^https?:\/\//.test(options.source)) {
    const url = `${options.source}/${options.ref}`;
    let response: Response;
    try {
      response = await fetch(url);
    } catch (error) {
      return fail(`${url}: ${reason(error)}`);
    }
    if (!response.ok) fail(`${url}: HTTP ${response.status}`);
    return Buffer.from(await response.arrayBuffer());
  }
  const archivePath = join(options.source, `${options.ref}.tar.gz`);
  try {
    return readFileSync(archivePath);
  } catch (error) {
    return fail(`${archivePath}: ${reason(error)}`);
  }
}

interface Header {
  path: string;
  size: number;
  type: string;
  mode: number;
}

/** Reads one 512-byte tar header. */
function readHeader(header: Buffer): Header {
  const field = (start: number, length: number): string =>
    header
      .subarray(start, start + length)
      .toString("utf8")
      .replace(/\0.*$/s, "");
  const posix = header.subarray(257, 263).toString("latin1") === "ustar\0";
  const prefix = posix ? field(345, 155) : "";
  return {
    path: prefix ? `${prefix}/${field(0, 100)}` : field(0, 100),
    size: Number.parseInt(field(124, 12).trim() || "0", 8),
    type: field(156, 1) || "0",
    mode: Number.parseInt(field(100, 8).trim() || "644", 8),
  };
}

function longNameOf(type: string, body: Buffer): string | undefined {
  if (type === "x") {
    return /(?:^|\n)\d+ path=([^\n]*)\n/.exec(body.toString("utf8"))?.[1];
  }
  return type === "L" ? body.toString("utf8").replace(/\0.*$/s, "") : undefined;
}

/**
 * Returns the regular files and links of a POSIX tar archive, with pax and GNU long names
 * applied. A link gets mode -1.
 */
function untar(archive: Buffer): Array<Entry> {
  const files: Array<Entry> = [];
  let offset = 0;
  let longName: string | undefined;
  while (offset + 512 <= archive.length) {
    const block = archive.subarray(offset, offset + 512);
    if (block.every((byte) => byte === 0)) break;
    const header = readHeader(block);
    const body = archive.subarray(offset + 512, offset + 512 + header.size);
    offset += 512 + Math.ceil(header.size / 512) * 512;
    if (header.type === "x" || header.type === "L") {
      longName = longNameOf(header.type, body);
      continue;
    }
    const path = longName ?? header.path;
    longName = undefined;
    if (header.type === "0" || header.type === "7") {
      files.push({ path, mode: header.mode, data: Buffer.from(body) });
    } else if (header.type === "1" || header.type === "2") {
      files.push({ path, mode: -1, data: Buffer.alloc(0) });
    }
  }
  return files;
}

/**
 * Rejects links and . or .. segments in selected paths after removing the top folder.
 */
function select(all: Array<Entry>): Array<Entry> {
  const chosen: Array<Entry> = [];
  for (const entry of all) {
    const parts = entry.path.split("/").filter(Boolean).slice(1);
    if (parts.length < 3 || !isArea(parts[0])) continue;
    if (parts.some((part) => part === "." || part === "..")) {
      fail(`Unsafe path in the archive: ${entry.path}`);
    }
    if (entry.mode < 0) fail(`Unsupported link in the archive: ${entry.path}`);
    chosen.push({ ...entry, path: parts.join("/") });
  }
  return chosen.sort((a, b) => a.path.localeCompare(b.path));
}

function isArea(name: string): name is Area {
  return name === "universes" || name === "skills";
}

function foldersOf(entries: Array<Entry>, area: Area): Array<string> {
  return [
    ...new Set(
      entries
        .filter((entry) => entry.path.startsWith(`${area}/`))
        .map((entry) => entry.path.split("/")[1]),
    ),
  ].sort();
}

function local(path: string): string {
  const [area, ...rest] = path.split("/");
  if (!isArea(area)) return fail(`Not under universes/ or skills/: ${path}`);
  return `${destination[area]}/${rest.join("/")}`;
}

function previousSkills(): Array<string> {
  const path = join(options.plugin, notesPath);
  if (!existsSync(path)) return [];
  return [
    ...readFileSync(path, "utf8").matchAll(
      /^\| `skills\/([^/`]+)\/` +\| `skills\/[^/`]+\/` +\|/gm,
    ),
  ].map((match) => match[1]);
}

/** Stages archive files before replacement so a staging failure preserves the current copy. */
function install(
  entries: Array<Entry>,
  folders: Record<Area, Array<string>>,
  notes: string,
): void {
  const stage = mkdtempSync(join(options.plugin, ".refresh-"));
  try {
    for (const entry of entries) {
      const target = join(stage, entry.path);
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, entry.data, {
        mode: entry.mode & 0o111 ? 0o755 : 0o644,
      });
    }
    const universes = join(options.plugin, destination.universes);
    rmSync(universes, { recursive: true, force: true });
    mkdirSync(dirname(universes), { recursive: true });
    renameSync(join(stage, "universes"), universes);
    const skills = join(options.plugin, destination.skills);
    mkdirSync(skills, { recursive: true });
    for (const folder of new Set([...previousSkills(), ...folders.skills])) {
      if (ownSkill.test(folder)) continue;
      rmSync(join(skills, folder), { recursive: true, force: true });
    }
    for (const folder of folders.skills) {
      renameSync(join(stage, "skills", folder), join(skills, folder));
    }
    writeFileSync(join(options.plugin, notesPath), notes);
  } finally {
    rmSync(stage, { recursive: true, force: true });
  }
}

async function upstreamNotes(
  entries: Array<Entry>,
  folders: Record<Area, Array<string>>,
): Promise<string> {
  const places = copied.flatMap((area) =>
    folders[area].map(
      (folder) =>
        `| \`${area}/${folder}/\` | \`${destination[area]}/${folder}/\` |`,
    ),
  );
  const hashes = entries.map(
    (entry) =>
      `| \`${local(entry.path)}\` | \`${createHash("sha256").update(entry.data).digest("hex")}\` |`,
  );
  return format(
    `# Upstream

Copied from [${repository}](https://github.com/${repository}) by \`just refresh_knowledge_model <tag>\`. Do not edit these files here. Change them upstream, then run the recipe with the new tag. The recipe fails when the tag differs from the knowledge-bus pin in \`${options.shown}/pyproject.toml\`.

| Upstream folder | Copied to |
| --- | --- |
${places.join("\n")}

## Ref, date and file hashes

- Ref: \`${options.ref}\`
- Fetched: ${new Date().toISOString().slice(0, 10)}

| File | SHA-256 |
| --- | --- |
${hashes.join("\n")}
`,
    { parser: "markdown" },
  );
}

/**
 * Prints `current: <path>` when every copied file matches UPSTREAM.md. Otherwise prints one line
 * per mismatched file and sets exit code 1.
 */
function check(): void {
  const notes = join(options.shown, notesPath);
  let text: string;
  try {
    text = readFileSync(join(options.plugin, notesPath), "utf8");
  } catch (error) {
    return fail(`${notes}: ${reason(error)}`);
  }
  const ref = /^- Ref: `([^`]+)`$/m.exec(text)?.[1] ?? readPin();
  const rerun = `run \`just refresh_knowledge_model ${ref}\`.`;
  const recorded = new Map(
    [...text.matchAll(/^\| `([^`]+)` +\| `([0-9a-f]{64})` +\|$/gm)].map(
      (match) => [match[1], match[2]],
    ),
  );
  const copies = [
    ...text.matchAll(
      /^\| `(?:universes|skills)\/[^`]+\/` +\| `([^`]+)\/` +\|$/gm,
    ),
  ].map((match) => match[1]);
  const faults: Array<string> = [];
  const found = new Set(copies.flatMap((folder) => filesUnder(folder)));
  for (const path of [...found].sort()) {
    const shown = join(options.shown, path);
    const hash = recorded.get(path);
    if (hash === undefined) {
      faults.push(`${shown} is not in ${notes}: delete the file, or ${rerun}`);
    } else if (hash !== sha256(join(options.plugin, path))) {
      faults.push(`${shown} does not match its SHA-256 in ${notes}: ${rerun}`);
    }
  }
  for (const path of [...recorded.keys()].filter((key) => !found.has(key))) {
    faults.push(
      `${join(options.shown, path)} is listed in ${notes} but missing: ${rerun}`,
    );
  }
  if (faults.length === 0) {
    console.log(`current: ${notes}`);
    return;
  }
  for (const fault of faults) console.error(fault);
  process.exitCode = 1;
}

/** Paths are relative to the plugin folder. */
function filesUnder(folder: string): Array<string> {
  const top = join(options.plugin, folder);
  if (!existsSync(top)) return [];
  return readdirSync(top, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) =>
      relative(options.plugin, join(entry.parentPath, entry.name)),
    );
}

function sha256(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}
