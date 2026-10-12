#!/usr/bin/env node

// Validates native `brew bottle --json` output; Homebrew still owns bottle merging.
// Filename contract: Homebrew/brew 7.0.9, Bottle::Filename in Library/Homebrew/bottle.rb.
import { createHash } from "node:crypto";
import {
  closeSync,
  constants,
  copyFileSync,
  fstatSync,
  lstatSync,
  mkdirSync,
  openSync,
  readFileSync,
  readSync,
  readdirSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const name = "knowledge-mcp";
const usage =
  "Usage: bottle-assets stage --metadata PATH --version VERSION --tag HOMEBREW_TAG --root-url URL --out DIR\n" +
  "       bottle-assets verify --dir DIR --version VERSION --root-url URL --tags arm64_sequoia,sequoia";
type ObjectValue = Record<string, unknown>;
interface Expected {
  version: string;
  rootUrl: string;
}
interface Metadata {
  text: string;
  fullName: string;
  formulaPath: string;
  tapGitPath: unknown;
  rebuild: number;
  tag: string;
  localName: string;
  remoteName: string;
  sha256: string;
}

function object(value: unknown, label: string): ObjectValue {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as ObjectValue;
}

function validateExpected(expected: Expected): void {
  if (!/^[A-Za-z0-9][A-Za-z0-9._+-]*$/.test(expected.version)) {
    throw new Error("version must be a safe Homebrew package version");
  }
  const url = new URL(expected.rootUrl);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    expected.rootUrl.endsWith("/")
  ) {
    throw new Error(
      "root URL must be an HTTPS asset directory without a trailing slash, credentials, query or fragment",
    );
  }
}

function validateTag(tag: string): void {
  if (!/^[a-z][a-z0-9_]*$/.test(tag)) {
    throw new Error(`invalid Homebrew tag: ${tag}`);
  }
}

export function readMetadata(path: string, expected: Expected): Metadata {
  if (!lstatSync(path).isFile())
    throw new Error(`metadata is not a regular file: ${path}`);
  const text = readFileSync(path, "utf8");
  const data = object(JSON.parse(text), "metadata");
  const keys = Object.keys(data);
  if (keys.length !== 1)
    throw new Error("metadata must contain exactly one formula");
  const fullName = keys[0];
  const qualified = /^([A-Za-z0-9_-]+)\/([A-Za-z0-9_-]+)\/knowledge-mcp$/.exec(
    fullName,
  );
  if (!qualified)
    throw new Error(
      "metadata must identify a fully qualified knowledge-mcp formula",
    );
  const entry = object(data[fullName], "formula entry");
  const formula = object(entry.formula, "formula");
  const bottle = object(entry.bottle, "bottle");
  if (formula.name !== name)
    throw new Error("formula.name must be knowledge-mcp");
  if (formula.pkg_version !== expected.version)
    throw new Error("formula package version differs from expected version");
  const formulaPath = formula.path;
  const prefix = `Library/Taps/${qualified[1]}/homebrew-${qualified[2]}/`;
  if (
    typeof formulaPath !== "string" ||
    !formulaPath.startsWith(`${prefix}Formula/`) ||
    !formulaPath.endsWith(`/${name}.rb`) ||
    formulaPath
      .split("/")
      .some((part) => !/^[A-Za-z0-9_-]+(?:\.rb)?$/.test(part))
  ) {
    throw new Error(
      "formula.path must be a safe path matching the fully qualified formula",
    );
  }
  if (
    formula.tap_git_path !== undefined &&
    formula.tap_git_path !== formulaPath.slice(prefix.length)
  ) {
    throw new Error("formula.tap_git_path differs from formula.path");
  }
  if (bottle.root_url !== expected.rootUrl)
    throw new Error("bottle root URL differs from expected root URL");
  if (!Number.isSafeInteger(bottle.rebuild) || (bottle.rebuild as number) < 0) {
    throw new Error("bottle rebuild must be a nonnegative safe integer");
  }
  if (typeof bottle.cellar !== "string" || !bottle.cellar) {
    throw new Error("bottle cellar must be a nonempty string");
  }
  const tags = object(bottle.tags, "bottle.tags");
  const tagNames = Object.keys(tags);
  if (tagNames.length !== 1)
    throw new Error("metadata must contain exactly one bottle tag");
  const tag = tagNames[0];
  validateTag(tag);
  const tagData = object(tags[tag], `bottle tag ${tag}`);
  const rebuild = bottle.rebuild as number;
  const suffix = `.${tag}.bottle${rebuild > 0 ? `.${rebuild}` : ""}.tar.gz`;
  const localName = `${name}--${expected.version}${suffix}`;
  const remoteName = `${name}-${expected.version}${suffix}`;
  if (tagData.local_filename !== localName)
    throw new Error("local_filename differs from the native Homebrew filename");
  // Compare with the encoded name generated from validated version/tag values.
  if (
    typeof tagData.filename !== "string" ||
    tagData.filename !== encodeURIComponent(remoteName)
  ) {
    throw new Error(
      "filename differs from the native Homebrew release asset filename",
    );
  }
  if (
    typeof tagData.sha256 !== "string" ||
    !/^[a-f0-9]{64}$/.test(tagData.sha256)
  ) {
    throw new Error("bottle sha256 must be 64 lowercase hexadecimal digits");
  }
  return {
    text,
    fullName,
    formulaPath,
    tapGitPath: formula.tap_git_path,
    rebuild,
    tag,
    localName,
    remoteName,
    sha256: tagData.sha256,
  };
}

/** Hash in bounded chunks rather than loading a bottle into memory. */
function verifyHash(path: string, sha256: string): void {
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    if (!fstatSync(fd).isFile())
      throw new Error(`archive is not a regular file: ${path}`);
    const hash = createHash("sha256");
    const chunk = Buffer.alloc(1024 * 1024);
    let count: number;
    while ((count = readSync(fd, chunk)) > 0)
      hash.update(chunk.subarray(0, count));
    if (hash.digest("hex") !== sha256)
      throw new Error(`SHA-256 mismatch: ${path}`);
  } finally {
    closeSync(fd);
  }
}

export function stage(
  options: Expected & { metadata: string; tag: string; out: string },
): Array<string> {
  validateExpected(options);
  validateTag(options.tag);
  const metadata = readMetadata(options.metadata, options);
  if (metadata.tag !== options.tag)
    throw new Error("bottle tag differs from expected tag");
  const source = join(dirname(resolve(options.metadata)), metadata.localName);
  verifyHash(source, metadata.sha256);
  mkdirSync(options.out, { recursive: true });
  const archive = join(options.out, metadata.remoteName);
  const localArchive = join(options.out, metadata.localName);
  const json = join(
    options.out,
    `${name}--${options.version}.${metadata.tag}.bottle.json`,
  );
  // Retain Homebrew's local archive name for native bottle tooling.
  copyFileSync(source, archive, constants.COPYFILE_EXCL);
  let copiedLocal = false;
  try {
    verifyHash(archive, metadata.sha256);
    copyFileSync(archive, localArchive, constants.COPYFILE_EXCL);
    copiedLocal = true;
    verifyHash(localArchive, metadata.sha256);
    writeFileSync(json, metadata.text, { flag: "wx" });
  } catch (error) {
    unlinkSync(archive);
    if (copiedLocal) unlinkSync(localArchive);
    throw error;
  }
  return [archive, localArchive, json];
}

function artifactFiles(dir: string): Array<string> {
  if (!lstatSync(dir).isDirectory())
    throw new Error(`artifact directory is not a regular directory: ${dir}`);
  return readdirSync(dir, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name))
    .flatMap((entry) => {
      const path = join(dir, entry.name);
      if (entry.isSymbolicLink())
        throw new Error(`artifact symlinks are not allowed: ${path}`);
      if (entry.isDirectory()) return artifactFiles(path);
      return [path];
    });
}

export function verify(
  options: Expected & { dir: string; tags: Array<string> },
): Array<string> {
  validateExpected(options);
  if (!options.tags.length) throw new Error("expected tags must not be empty");
  options.tags.forEach(validateTag);
  const wanted = new Set(options.tags);
  if (wanted.size !== options.tags.length)
    throw new Error("expected tags contain duplicates");
  const inventory = artifactFiles(options.dir);
  const files = inventory.filter((path) => path.endsWith(".bottle.json"));
  const archives = new Set(
    inventory.filter(
      (path) => path.endsWith(".tar.gz") && basename(path).includes(".bottle"),
    ),
  );
  const allowedArchives = new Set<string>();
  const seen = new Set<string>();
  let first: Metadata | undefined;
  for (const path of files) {
    const metadata = readMetadata(path, options);
    if (!wanted.has(metadata.tag))
      throw new Error(`unexpected bottle tag: ${metadata.tag}`);
    if (seen.has(metadata.tag))
      throw new Error(`duplicate bottle tag: ${metadata.tag}`);
    if (
      first &&
      (metadata.fullName !== first.fullName ||
        metadata.formulaPath !== first.formulaPath ||
        metadata.tapGitPath !== first.tapGitPath ||
        metadata.rebuild !== first.rebuild)
    ) {
      throw new Error(
        "matrix metadata has inconsistent formula identity, path or bottle rebuild",
      );
    }
    first ??= metadata;
    seen.add(metadata.tag);
    const parent = dirname(path);
    // Uploaded matrix artifacts contain release asset names. Original native names
    // may also be retained for `brew bottle --merge`; verify each when present.
    const names = [metadata.remoteName, metadata.localName].map((file) =>
      join(parent, file),
    );
    names.forEach((archivePath) => allowedArchives.add(archivePath));
    const candidates = names.filter((archivePath) => archives.has(archivePath));
    if (!candidates.length)
      throw new Error(`missing bottle archive for tag: ${metadata.tag}`);
    for (const archive of candidates) verifyHash(archive, metadata.sha256);
  }
  const missing = [...wanted].filter((tag) => !seen.has(tag));
  if (missing.length)
    throw new Error(`missing bottle tags: ${missing.join(", ")}`);
  for (const archive of archives) {
    if (!allowedArchives.has(archive))
      throw new Error(`unexpected bottle archive filename: ${archive}`);
  }
  return files;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const { values, positionals } = parseArgs({
      allowPositionals: true,
      options: {
        metadata: { type: "string" },
        version: { type: "string" },
        tag: { type: "string" },
        "root-url": { type: "string" },
        out: { type: "string" },
        dir: { type: "string" },
        tags: { type: "string" },
      },
    });
    const [command] = positionals;
    if (positionals.length !== 1 || !values.version || !values["root-url"])
      throw new Error(usage);
    const expected = { version: values.version, rootUrl: values["root-url"] };
    if (
      command === "stage" &&
      values.metadata &&
      values.tag &&
      values.out &&
      !values.dir &&
      !values.tags
    ) {
      console.log(
        stage({
          ...expected,
          metadata: values.metadata,
          tag: values.tag,
          out: values.out,
        }).join("\n"),
      );
    } else if (
      command === "verify" &&
      values.dir &&
      values.tags &&
      !values.metadata &&
      !values.tag &&
      !values.out
    ) {
      console.log(
        verify({
          ...expected,
          dir: values.dir,
          tags: values.tags.split(","),
        }).join("\n"),
      );
    } else throw new Error(usage);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
