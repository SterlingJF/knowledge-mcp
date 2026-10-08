#!/usr/bin/env node

// Copies the knowledge-bus protocol, universe, and type guidance at a ref into the vendored
// upstream folder, under the file names the server loads, and rewrites its UPSTREAM.md.
// Nothing is written unless all three files are read.

import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { parseArgs } from "node:util";

import { format } from "prettier";

const repository = "SterlingJF/knowledge-bus";
const defaultSource = `https://raw.githubusercontent.com/${repository}`;
const defaultDest = "contracts/extensions/knowledge-bus/upstream";

// Upstream path -> local name (the vault-starter convention).
const files = [
  {
    upstream: "protocol/knowledge-bus-protocol.yaml",
    local: "Knowledge Bus Protocol (KBP).yaml",
  },
  {
    upstream: "universes/product-development/universe.kbp.yaml",
    local: "Artifact Universe.kbp.yaml",
  },
  {
    upstream: "universes/product-development/type-guidance.kbp.yaml",
    local: "Artifact Universe.type-guidance.kbp.yaml",
  },
] as const;

const usage =
  "Usage: refresh-knowledge-model --ref <branch|tag|commit> [--source <url-or-dir>] [--dest <dir>]";

const options = readArgs();
const fetched = await Promise.all(
  files.map(async (file) => ({
    ...file,
    bytes: await read(`${options.ref}/${file.upstream}`),
  })),
);

mkdirSync(options.dest, { recursive: true });
for (const file of fetched) {
  writeFileSync(join(options.dest, file.local), file.bytes);
  console.log(`wrote: ${file.local} <- ${file.upstream}@${options.ref}`);
}
writeFileSync(join(options.dest, "UPSTREAM.md"), await upstreamNotes());
console.log("wrote: UPSTREAM.md");

function readArgs(): { ref: string; source: string; dest: string } {
  try {
    const { values } = parseArgs({
      options: {
        ref: { type: "string" },
        source: { type: "string", default: defaultSource },
        dest: { type: "string", default: defaultDest },
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
      source: values.source.replace(/\/+$/, ""),
      dest: resolve(values.dest),
    };
  } catch {
    return fail(usage);
  }
}

/** Reads `<source>/<path>` over HTTP(S), or from a local directory. */
async function read(path: string): Promise<Buffer> {
  if (/^https?:\/\//.test(options.source)) {
    const url = `${options.source}/${path}`;
    let response: Response;
    try {
      response = await fetch(url);
    } catch (error) {
      return fail(`${url}: ${error instanceof Error ? error.message : error}`);
    }
    if (!response.ok) fail(`${url}: HTTP ${response.status}`);
    return Buffer.from(await response.arrayBuffer());
  }
  const local = join(options.source, path);
  try {
    return readFileSync(local);
  } catch (error) {
    return fail(`${local}: ${(error as NodeJS.ErrnoException).code ?? error}`);
  }
}

async function upstreamNotes(): Promise<string> {
  const paths = fetched.map(
    (file) => `| \`${file.local}\` | \`${file.upstream}\` |`,
  );
  const hashes = fetched.map(
    (file) =>
      `| \`${file.local}\` | \`${createHash("sha256").update(file.bytes).digest("hex")}\` |`,
  );
  return format(
    `# Upstream

Vendored read-only from [${repository}](https://github.com/${repository}). Do not edit these files here; change them upstream, then run \`just refresh_knowledge_model <ref>\`.

| File | Path when vendored |
| --- | --- |
${paths.join("\n")}

The engine loads every \`*.kbp.yaml\` file here. \`km-server\` bundles this folder as \`knowledge-model/\`.

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
