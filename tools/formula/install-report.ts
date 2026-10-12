#!/usr/bin/env node

// Times the target installation after runtime and build dependencies are installed.
import { execFileSync } from "node:child_process";
import { closeSync, openSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

export type Runner = (
  command: string,
  args: Array<string>,
  options?: { cwd?: string; log?: string },
) => string;

interface InstallOptions {
  formula: string;
  version: string;
  kind: "source" | "bottle";
  tag: string;
  commit: string;
  out: string;
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function measureInstall(
  options: InstallOptions,
  execute: Runner,
  now: () => number = () => performance.now(),
) {
  if (!/^[a-f0-9]{40}$/.test(options.commit)) {
    throw new Error("--commit must be the full source commit SHA");
  }
  const started = now();
  execute(
    "brew",
    [
      "install",
      ...(options.kind === "source" ? ["--build-from-source"] : []),
      options.formula,
    ],
    { log: options.out.replace(/\.json$/, ".log") },
  );
  const elapsed = (now() - started) / 1000;
  const info: unknown = JSON.parse(
    execute("brew", ["info", "--json=v2", options.formula]),
  );
  let receipt: unknown;
  if (
    record(info) &&
    Array.isArray(info.formulae) &&
    info.formulae.length === 1
  ) {
    const entry: unknown = info.formulae.at(0);
    if (
      record(entry) &&
      Array.isArray(entry.installed) &&
      entry.installed.length === 1
    ) {
      receipt = entry.installed.at(0);
    }
  }
  if (!record(receipt) || receipt.version !== options.version) {
    throw new Error(
      "installed version differs from the released package version",
    );
  }
  if (receipt.poured_from_bottle !== (options.kind === "bottle")) {
    throw new Error(
      "Homebrew did not perform the requested " + options.kind + " install",
    );
  }
  const prefix = execute("brew", ["--prefix", options.formula]).trim();
  const kbVersion = execute(join(prefix, "bin/kb"), ["--version"]).trim();
  const report = {
    arch: execute("uname", ["-m"]).trim(),
    macos: execute("sw_vers", ["-productVersion"]).trim(),
    bottle_tag: options.tag,
    kind: options.kind,
    elapsed_seconds: Math.round(elapsed * 1000) / 1000,
    dependency_state: "runtime-and-build-preinstalled",
    kb_version: kbVersion,
    source_commit: options.commit,
  };
  writeFileSync(options.out, JSON.stringify(report, null, 2) + "\n");
  return report;
}

const run: Runner = (command, args, options) => {
  if (options?.log) {
    const output = openSync(options.log, "w");
    try {
      execFileSync(command, args, {
        cwd: options.cwd,
        stdio: ["ignore", output, output],
      });
      return "";
    } finally {
      closeSync(output);
    }
  }
  return execFileSync(command, args, { cwd: options?.cwd, encoding: "utf8" });
};

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const { values } = parseArgs({
      options: {
        formula: { type: "string" },
        version: { type: "string" },
        kind: { type: "string" },
        tag: { type: "string" },
        commit: { type: "string" },
        out: { type: "string" },
      },
    });
    for (const key of ["formula", "version", "tag", "commit", "out"] as const) {
      if (!values[key]) throw new Error("--" + key + " is required");
    }
    if (values.kind !== "source" && values.kind !== "bottle") {
      throw new Error("--kind must be source or bottle");
    }
    const report = measureInstall(
      {
        formula: values.formula!,
        version: values.version!,
        kind: values.kind,
        tag: values.tag!,
        commit: values.commit!,
        out: values.out!,
      },
      run,
    );
    console.log(JSON.stringify(report));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode =
      record(error) && typeof error.status === "number" && error.status > 0
        ? error.status
        : 1;
  }
}
