#!/usr/bin/env node

import {
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { constants, tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

import { parseAllDocuments, stringify } from "yaml";
import type { Document } from "yaml";

type Yaml = string | number | boolean | null | ReadonlyArray<Yaml> | Mapping;
interface Mapping {
  readonly [key: string]: Yaml;
}

function isMapping<Value>(value: Value): value is Value & Mapping {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isLockfileVersion(version: Yaml | undefined): boolean {
  return (
    (typeof version === "string" && /^\d+(?:\.\d+)?$/.test(version)) ||
    (typeof version === "number" && Number.isFinite(version) && version > 0)
  );
}

/** Throws on a YAML error or a non-mapping document. The message names the document. */
function parseDocument(document: Document.Parsed, location: string): Mapping {
  if (document.errors.length > 0) {
    throw new Error(
      `${location}: ${document.errors.map((error) => error.message).join("; ")}`,
    );
  }
  let value: unknown;
  try {
    value = document.toJS();
  } catch (error) {
    throw new Error(
      `${location}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (!isMapping(value))
    throw new Error(`${location}: expected a lockfile mapping`);
  return value;
}

function isMappingOfMappings(value: Yaml | undefined): value is Mapping {
  return isMapping(value) && Object.values(value).every(isMapping);
}

function checkLock(value: Mapping, location: string): void {
  if (!isLockfileVersion(value.lockfileVersion)) {
    throw new Error(`${location}: missing or invalid lockfileVersion`);
  }
  const importers = value.importers;
  if (!isMappingOfMappings(importers) || Object.keys(importers).length === 0) {
    throw new Error(
      `${location}: expected importers to be a nonempty mapping of mappings`,
    );
  }
  for (const key of ["packages", "snapshots"]) {
    if (key in value && !isMappingOfMappings(value[key])) {
      throw new Error(
        `${location}: expected every ${key} entry to be a mapping`,
      );
    }
  }
  if ("settings" in value && !isMapping(value.settings)) {
    throw new Error(`${location}: expected a settings mapping`);
  }
}

function readLockDocuments(path: string): Array<Mapping> {
  const documents = parseAllDocuments(readFileSync(path, "utf8"));
  if (documents.length === 0) throw new Error(`${path}: no lockfile documents`);
  return documents.map((document, index) => {
    const location = `${path}, document ${index + 1}`;
    const value = parseDocument(document, location);
    checkLock(value, location);
    return value;
  });
}

function findCargoLockfiles(directory: string): Array<string> {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name.startsWith(".") ||
        entry.name === "node_modules" ||
        entry.name === "target"
        ? []
        : findCargoLockfiles(path);
    }
    return entry.isFile() && entry.name === "Cargo.lock" ? [path] : [];
  });
}

/**
 * Returns the scanner's exit code, 127 for a missing scanner, or 1 for another spawn error.
 * Returns 128 plus the signal number when a signal stops the scanner.
 * Writes each pnpm-lock.yaml document to a temporary file because the scanner reads one YAML document per file.
 */
export function scanDependencies(
  options: { rootDir?: string; scanner?: string } = {},
): number {
  const root = resolve(options.rootDir ?? process.cwd());
  const documents = readLockDocuments(join(root, "pnpm-lock.yaml"));
  const temporary = mkdtempSync(join(tmpdir(), "dependency-lockfiles-"));
  try {
    const lockfiles = documents.map((document, index) => {
      const directory = join(temporary, String(index + 1));
      mkdirSync(directory);
      const path = join(directory, "pnpm-lock.yaml");
      writeFileSync(path, stringify(document));
      return path;
    });
    const result = spawnSync(
      options.scanner ?? "osv-scanner",
      [
        "scan",
        "source",
        ...lockfiles.flatMap((path) => ["--lockfile", path]),
        "--lockfile",
        join(root, "uv.lock"),
        ...findCargoLockfiles(root)
          .sort()
          .flatMap((path) => ["--lockfile", path]),
        "--config",
        join(root, "osv-scanner.toml"),
      ],
      { cwd: root, stdio: "inherit" },
    );
    if (result.error) {
      console.error(result.error.message);
      return "code" in result.error && result.error.code === "ENOENT" ? 127 : 1;
    }
    if (result.signal) {
      const signals: Partial<typeof constants.signals> = constants.signals;
      return 128 + (signals[result.signal] ?? 1);
    }
    return result.status ?? 1;
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  if (process.argv.length > 2) {
    console.error(
      "Usage: node tools/dependencies/scan-dependencies.ts (run from the repo root, no arguments)",
    );
    process.exitCode = 1;
  } else {
    try {
      process.exitCode = scanDependencies();
    } catch (error) {
      console.error(error instanceof Error ? error.message : error);
      process.exitCode = 1;
    }
  }
}
