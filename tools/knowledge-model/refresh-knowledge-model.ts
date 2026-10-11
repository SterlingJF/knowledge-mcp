#!/usr/bin/env node

// Copies every folder under knowledge-bus's universes/ and skills/ at a ref into the plugin
// folder: universe specs to knowledge-bus/universes/<name>/, skills to skills/<name>/, under
// their upstream names. Records the ref, the date and each file's SHA-256 in
// knowledge-bus/UPSTREAM.md. Downloads GitHub's tarball for the ref; runs no git.
// Refuses a ref that differs from the tag of the knowledge-bus release archive the plugin's
// pyproject.toml pins, and
// writes nothing unless the whole archive is read. Skill folders named km-* belong to
// knowledge-mcp: the refresh leaves them in place and refuses an upstream skill with such a name.

import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { gunzipSync } from "node:zlib";

import { format } from "prettier";

const repository = "SterlingJF/knowledge-bus";
const defaultSource = `https://codeload.github.com/${repository}/tar.gz`;
const copied = ["universes", "skills"] as const;
type Area = (typeof copied)[number];

/** Where each upstream area lands, relative to the plugin folder. */
const destination: Record<Area, string> = {
  universes: "knowledge-bus/universes",
  skills: "skills",
};
const notesPath = "knowledge-bus/UPSTREAM.md";
/** Skill folders knowledge-mcp writes itself. */
const ownSkill = /^km-/;

const usage =
  "Usage: refresh-knowledge-model --ref <branch|tag|commit> [--plugin <dir>] [--source <url-or-dir>]";

interface Entry {
  path: string;
  mode: number;
  data: Buffer;
}

const options = readArgs();
const pin = readPin();
if (pin !== options.ref) {
  fail(
    `The ref ${options.ref} differs from the knowledge-bus pin ${pin} in ${join(options.plugin, "pyproject.toml")}. ` +
      "Change the pin and run uv lock first, so the package and the copies come from one release.",
  );
}
const entries = select(untar(gunzipSync(await read())));
const folders = Object.fromEntries(
  copied.map((area) => [area, foldersOf(area)]),
) as Record<Area, string[]>;
for (const area of copied) {
  if (folders[area].length === 0)
    fail(`The archive has no folders under ${area}/.`);
}
for (const folder of folders.skills.filter((name) => ownSkill.test(name))) {
  fail(
    `The archive has skills/${folder}/, a name that belongs to knowledge-mcp's own skills. Rename it upstream.`,
  );
}
const notes = await upstreamNotes();
install();
for (const area of copied) {
  for (const folder of folders[area]) {
    console.log(
      `wrote: ${destination[area]}/${folder}/ <- ${area}/${folder}/@${options.ref}`,
    );
  }
}
console.log(`wrote: ${notesPath}`);

function readArgs(): { ref: string; plugin: string; source: string } {
  try {
    const { values } = parseArgs({
      options: {
        ref: { type: "string" },
        plugin: { type: "string", default: "runtime" },
        source: { type: "string", default: defaultSource },
      },
      strict: true,
    });
    if (!values.ref) fail(usage);
    if (
      !/^[\w.-]+(?:\/[\w.-]+)*$/.test(values.ref) ||
      /(^|\/)\.\.?(\/|$)/.test(values.ref)
    ) {
      fail(`Not a ref: ${values.ref}`);
    }
    return {
      ref: values.ref,
      plugin: resolve(values.plugin),
      source: values.source.replace(/\/+$/, ""),
    };
  } catch {
    return fail(usage);
  }
}

/** The tag in the plugin's `knowledge-bus @ https://github.com/.../releases/download/<tag>/...` dependency. */
function readPin(): string {
  const path = join(options.plugin, "pyproject.toml");
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (error) {
    return fail(`${path}: ${(error as NodeJS.ErrnoException).code ?? error}`);
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

/** The tarball for the ref, over HTTPS, or `<dir>/<ref>.tar.gz` from a local directory. */
async function read(): Promise<Buffer> {
  if (/^https?:\/\//.test(options.source)) {
    const url = `${options.source}/${options.ref}`;
    let response: Response;
    try {
      response = await fetch(url);
    } catch (error) {
      return fail(`${url}: ${error instanceof Error ? error.message : error}`);
    }
    if (!response.ok) fail(`${url}: HTTP ${response.status}`);
    return Buffer.from(await response.arrayBuffer());
  }
  const local = join(options.source, `${options.ref}.tar.gz`);
  try {
    return readFileSync(local);
  } catch (error) {
    return fail(`${local}: ${(error as NodeJS.ErrnoException).code ?? error}`);
  }
}

/** Every regular file in a POSIX tar archive, with pax and GNU long names applied. */
function untar(archive: Buffer): Entry[] {
  const files: Entry[] = [];
  let offset = 0;
  let longName: string | undefined;
  while (offset + 512 <= archive.length) {
    const header = archive.subarray(offset, offset + 512);
    if (header.every((byte) => byte === 0)) break;
    const field = (start: number, length: number): string =>
      header
        .subarray(start, start + length)
        .toString("utf8")
        .replace(/\0.*$/s, "");
    const size = Number.parseInt(field(124, 12).trim() || "0", 8);
    const type = field(156, 1) || "0";
    const posix = header.subarray(257, 263).toString("latin1") === "ustar\0";
    const prefix = posix ? field(345, 155) : "";
    const body = archive.subarray(offset + 512, offset + 512 + size);
    offset += 512 + Math.ceil(size / 512) * 512;
    if (type === "x") {
      longName = /(?:^|\n)\d+ path=([^\n]*)\n/.exec(body.toString("utf8"))?.[1];
      continue;
    }
    if (type === "L") {
      longName = body.toString("utf8").replace(/\0.*$/s, "");
      continue;
    }
    const path =
      longName ?? (prefix ? `${prefix}/${field(0, 100)}` : field(0, 100));
    longName = undefined;
    if (type === "0" || type === "7") {
      files.push({
        path,
        mode: Number.parseInt(field(100, 8).trim() || "644", 8),
        data: Buffer.from(body),
      });
    } else if (type === "1" || type === "2") {
      files.push({ path, mode: -1, data: Buffer.alloc(0) });
    }
  }
  return files;
}

/** Files under universes/<folder>/ and skills/<folder>/, without the archive's top folder. */
function select(all: Entry[]): Entry[] {
  const chosen: Entry[] = [];
  for (const entry of all) {
    const parts = entry.path.split("/").filter(Boolean).slice(1);
    if (parts.length < 3 || !(copied as readonly string[]).includes(parts[0])) {
      continue;
    }
    if (parts.some((part) => part === "." || part === "..")) {
      fail(`Unsafe path in the archive: ${entry.path}`);
    }
    if (entry.mode < 0) fail(`Links are not copied: ${entry.path}`);
    chosen.push({ ...entry, path: parts.join("/") });
  }
  return chosen.sort((a, b) => a.path.localeCompare(b.path));
}

function foldersOf(area: Area): string[] {
  return [
    ...new Set(
      entries
        .filter((entry) => entry.path.startsWith(`${area}/`))
        .map((entry) => entry.path.split("/")[1]),
    ),
  ].sort();
}

/** The local path of an upstream file, relative to the plugin folder. */
function local(path: string): string {
  const [area, ...rest] = path.split("/");
  return `${destination[area as Area]}/${rest.join("/")}`;
}

/** Skill folders the last refresh copied, from its UPSTREAM.md. */
function previousSkills(): string[] {
  const path = join(options.plugin, notesPath);
  if (!existsSync(path)) return [];
  return [
    ...readFileSync(path, "utf8").matchAll(
      /^\| `skills\/([^/`]+)\/` +\| `skills\/[^/`]+\/` +\|/gm,
    ),
  ].map((match) => match[1]);
}

/** Stage every file, then swap the copies into place. */
function install(): void {
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

async function upstreamNotes(): Promise<string> {
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

Copied read-only from [${repository}](https://github.com/${repository}) by \`just refresh_knowledge_model <ref>\`. Change these files upstream, then run the recipe with the new ref. The recipe refuses a tag that differs from the knowledge-bus release archive pinned in \`pyproject.toml\`, so the \`kbp\` package and these copies come from one release.

| Upstream folder | Copied to |
| --- | --- |
${places.join("\n")}

## Ref and Date

- Ref: \`${options.ref}\`
- Fetched: ${new Date().toISOString().slice(0, 10)}

| File | SHA-256 |
| --- | --- |
${hashes.join("\n")}
`,
    { parser: "markdown" },
  );
}

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}
