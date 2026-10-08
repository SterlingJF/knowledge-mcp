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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readLockDocuments(path: string): Record<string, unknown>[] {
  const documents = parseAllDocuments(readFileSync(path, "utf8"));
  if (documents.length === 0) throw new Error(`${path}: no lockfile documents`);
  return documents.map((document, index) => {
    const location = `${path}, document ${index + 1}`;
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
        `${location}: ${error instanceof Error ? error.message : error}`,
      );
    }
    if (!isRecord(value))
      throw new Error(`${location}: expected a lockfile mapping`);
    const version = value.lockfileVersion;
    if (!(
      (typeof version === "string" && /^\d+(?:\.\d+)?$/.test(version)) ||
      (typeof version === "number" && Number.isFinite(version) && version > 0)
    )) {
      throw new Error(`${location}: missing or invalid lockfileVersion`);
    }
    if (
      !isRecord(value.importers) ||
      Object.keys(value.importers).length === 0 ||
      !Object.values(value.importers).every(isRecord)
    ) {
      throw new Error(`${location}: expected nonempty importer mappings`);
    }
    for (const key of ["packages", "snapshots"]) {
      if (
        key in value &&
        (!isRecord(value[key]) || !Object.values(value[key]).every(isRecord))
      ) {
        throw new Error(`${location}: expected ${key} mappings`);
      }
    }
    if ("settings" in value && !isRecord(value.settings)) {
      throw new Error(`${location}: expected a settings mapping`);
    }
    return value;
  });
}

/** Every Cargo.lock outside hidden, node_modules and target folders. */
function findCargoLockfiles(directory: string): string[] {
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

/** Split every pnpm document for scanners that only understand one YAML document. */
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
      return (result.error as NodeJS.ErrnoException).code === "ENOENT"
        ? 127
        : 1;
    }
    if (result.signal) return 128 + (constants.signals[result.signal] ?? 1);
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
    console.error("Usage: scan-dependencies (scans the current repository)");
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
