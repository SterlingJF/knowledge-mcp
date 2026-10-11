#!/usr/bin/env node

// Writes the Homebrew formula for knowledge-mcp from the package's source archive and uv.lock.
// The formula builds everything from source: knowledge-mcp from its release archive, and one
// resource per Python package the plugin's requirements.lock installs on macOS, each from the
// source archive uv.lock records (knowledge-bus from its own release archive). It refuses a
// package uv.lock holds no source archive for, and a version that differs from pyproject.toml.

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { parse } from "smol-toml";

const repository = "SterlingJF/knowledge-mcp";
const description =
  "Help agent apps read, write and bring in knowledge with universe specs";
const usage =
  "Usage: generate-formula --sdist <knowledge_mcp-<version>.tar.gz> --out <Formula/knowledge-mcp.rb> " +
  "[--url <release asset url>] [--lock uv.lock] [--requirements runtime/requirements.lock] " +
  "[--pyproject runtime/pyproject.toml]";

/** Native libraries and build tools some source archives need, by package name. */
const native: Record<string, { build?: string[]; run?: string[] }> = {
  cryptography: { build: ["pkgconf", "rust"], run: ["openssl@3"] },
  "pydantic-core": { build: ["rust"] },
  "rpds-py": { build: ["rust"] },
  pyyaml: { run: ["libyaml"] },
};

/** The environment markers of the Python the formula installs into: CPython 3.14 on macOS. */
const environment: Record<string, string> = {
  sys_platform: "darwin",
  platform_system: "Darwin",
  os_name: "posix",
  platform_python_implementation: "CPython",
  implementation_name: "cpython",
  python_version: "3.14",
  python_full_version: "3.14.0",
};

export interface Requirement {
  name: string;
  version?: string;
  url?: string;
}

export interface Resource {
  name: string;
  url: string;
  sha256: string;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const options = readArgs();
  const formula = generate({
    sdist: readFileSync(options.sdist),
    url: options.url,
    lock: readFileSync(options.lock, "utf8"),
    requirements: readFileSync(options.requirements, "utf8"),
    pyproject: readFileSync(options.pyproject, "utf8"),
  });
  writeFileSync(options.out, formula);
  console.log(`wrote: ${options.out}`);
}

function readArgs() {
  try {
    const { values } = parseArgs({
      options: {
        sdist: { type: "string" },
        out: { type: "string" },
        url: { type: "string" },
        lock: { type: "string", default: "uv.lock" },
        requirements: {
          type: "string",
          default: "runtime/requirements.lock",
        },
        pyproject: { type: "string", default: "runtime/pyproject.toml" },
      },
      strict: true,
    });
    if (!values.sdist || !values.out) fail(usage);
    return values as Required<typeof values>;
  } catch (error) {
    return fail(error instanceof Error ? `${error.message}\n${usage}` : usage);
  }
}

export function generate(input: {
  sdist: Buffer;
  url?: string;
  lock: string;
  requirements: string;
  pyproject: string;
}): string {
  const project = (
    parse(input.pyproject) as { project: Record<string, unknown> }
  ).project;
  const version = String(project.version);
  const url =
    input.url ??
    `https://github.com/${repository}/releases/download/v${version}/knowledge_mcp-${version}.tar.gz`;
  if (!url.includes(`knowledge_mcp-${version}.tar.gz`)) {
    fail(`${url} is not the source archive of knowledge-mcp ${version}.`);
  }
  const sha256 = createHash("sha256").update(input.sdist).digest("hex");
  const resources = resolve(requirementsFor(input.requirements), input.lock);
  return render({
    url,
    sha256,
    resources,
  });
}

/** The packages requirements.lock installs on macOS with CPython 3.14. */
export function requirementsFor(text: string): Requirement[] {
  const found: Requirement[] = [];
  const joined = text.replace(/\\\n/g, " ");
  for (const raw of joined.split("\n")) {
    const line = raw.replace(/\s+--hash=\S+/g, "").trim();
    if (!line || line.startsWith("#")) continue;
    const [requirement, marker] = line.split(/\s;\s/, 2);
    if (marker !== undefined && !evaluate(marker)) continue;
    const pinned = /^([A-Za-z0-9._-]+)==(\S+)$/.exec(requirement.trim());
    const direct = /^([A-Za-z0-9._-]+)\s*@\s*(\S+)$/.exec(requirement.trim());
    if (pinned) found.push({ name: normal(pinned[1]), version: pinned[2] });
    else if (direct) found.push({ name: normal(direct[1]), url: direct[2] });
    else fail(`requirements.lock: can't read ${JSON.stringify(line)}`);
  }
  return found;
}

/** Each requirement's source archive and SHA-256, from uv.lock. */
export function resolve(
  requirements: Requirement[],
  lockText: string,
): Resource[] {
  const lock = parse(lockText) as {
    package?: {
      name: string;
      version: string;
      source?: { url?: string };
      sdist?: { url?: string; hash?: string };
    }[];
  };
  const packages = lock.package ?? [];
  return requirements
    .map((requirement) => {
      const entry = packages.find(
        (item) =>
          normal(item.name) === requirement.name &&
          (requirement.version === undefined ||
            item.version === requirement.version) &&
          (requirement.url === undefined ||
            item.source?.url === requirement.url),
      );
      if (!entry) {
        return fail(
          `uv.lock has no ${requirement.name} ${requirement.version ?? requirement.url}.`,
        );
      }
      const url = entry.sdist?.url ?? entry.source?.url;
      const hash = entry.sdist?.hash;
      if (
        !url ||
        !hash?.startsWith("sha256:") ||
        !/\.(tar\.gz|zip)$/.test(url)
      ) {
        return fail(
          `uv.lock records no source archive for ${entry.name} ${entry.version}; the formula builds from source.`,
        );
      }
      return { name: entry.name, url, sha256: hash.slice("sha256:".length) };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

function normal(name: string): string {
  return name.toLowerCase().replace(/[-_.]+/g, "-");
}

/** A PEP 508 marker: comparisons joined by `and`, `or` and parentheses. */
export function evaluate(marker: string): boolean {
  const tokens =
    marker.match(
      /\(|\)|'[^']*'|"[^"]*"|[=!<>]=|<|>|~=|\bnot in\b|\bin\b|\band\b|\bor\b|[A-Za-z_][A-Za-z0-9_.]*/g,
    ) ?? [];
  let at = 0;
  const peek = (): string | undefined => tokens[at];
  const next = (): string => {
    const token = tokens[at++];
    if (token === undefined) fail(`marker ends early: ${marker}`);
    return token;
  };
  const value = (token: string): string => {
    if (/^['"]/.test(token)) return token.slice(1, -1);
    if (!(token in environment))
      fail(`unknown marker variable ${token} in ${marker}`);
    return environment[token];
  };
  const compare = (left: string, op: string, right: string): boolean => {
    const numeric = /^\d+(\.\d+)*$/.test(left) && /^\d+(\.\d+)*$/.test(right);
    const order = numeric
      ? versionOrder(left, right)
      : left.localeCompare(right);
    switch (op) {
      case "==":
        return order === 0;
      case "!=":
        return order !== 0;
      case "<":
        return numeric && order < 0;
      case "<=":
        return numeric && order <= 0;
      case ">":
        return numeric && order > 0;
      case ">=":
        return numeric && order >= 0;
      case "in":
        return right.includes(left);
      case "not in":
        return !right.includes(left);
      default:
        return fail(`unsupported marker operator ${op} in ${marker}`);
    }
  };
  const atom = (): boolean => {
    if (peek() === "(") {
      next();
      const result = either();
      if (next() !== ")") fail(`unbalanced marker: ${marker}`);
      return result;
    }
    const left = value(next());
    const op = next();
    const right = value(next());
    return compare(left, op, right);
  };
  const both = (): boolean => {
    let result = atom();
    while (peek() === "and") {
      next();
      result = atom() && result;
    }
    return result;
  };
  const either = (): boolean => {
    let result = both();
    while (peek() === "or") {
      next();
      result = both() || result;
    }
    return result;
  };
  const result = either();
  if (at !== tokens.length) fail(`can't read marker: ${marker}`);
  return result;
}

function versionOrder(left: string, right: string): number {
  const a = left.split(".").map(Number);
  const b = right.split(".").map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const difference = (a[i] ?? 0) - (b[i] ?? 0);
    if (difference !== 0) return Math.sign(difference);
  }
  return 0;
}

function render(input: {
  url: string;
  sha256: string;
  resources: Resource[];
}): string {
  const build = new Set<string>();
  const run = new Set<string>(["python@3.14"]);
  for (const resource of input.resources) {
    for (const name of native[resource.name]?.build ?? []) build.add(name);
    for (const name of native[resource.name]?.run ?? []) run.add(name);
  }
  const depends = [
    ...[...build].sort().map((name) => `  depends_on "${name}" => :build`),
    ...[...run].sort().map((name) => `  depends_on "${name}"`),
  ];
  const resources = input.resources.map(
    (resource) =>
      `  resource "${resource.name}" do\n    url "${resource.url}"\n    sha256 "${resource.sha256}"\n  end\n`,
  );
  return `# Generated from uv.lock by tools/formula/generate-formula.ts in ${repository}; do not edit.
class KnowledgeMcp < Formula
  include Language::Python::Virtualenv

  desc "${description}"
  homepage "https://github.com/${repository}"
  url "${input.url}"
  sha256 "${input.sha256}"
  license "MIT"

${depends.join("\n")}

${resources.join("\n")}
  def install
    virtualenv_install_with_resources
    # Host settings and skill links name opt paths, which \`brew upgrade\` moves to the new version.
    site_packages = Language::Python.site_packages("python3.14")
    (bin/"kb").unlink
    (bin/"kb").write_env_script libexec/"bin/kb",
                                KNOWLEDGE_MCP_COMMAND: opt_bin/"kb",
                                KNOWLEDGE_MCP_DATA:    opt_libexec/site_packages/"knowledge_mcp"
  end

  def caveats
    <<~EOS
      Register knowledge-mcp with each agent app you use on this Mac:
        kb setup claude-code
        kb setup codex
        kb setup claude-desktop
        kb setup pi
        kb setup opencode
      Before \`brew uninstall knowledge-mcp\`, run \`kb setup --remove <host>\` for each app.
      Your answer log and edit record stay after the uninstall, in $KNOWLEDGE_MCP_STATE_DIR when set,
      else $XDG_STATE_HOME/knowledge-mcp, else ~/.local/state/knowledge-mcp. \`kb doctor\` shows the folder in use.
    EOS
  end

  test do
    assert_match "kb #{version}", shell_output("#{bin}/kb --version")
    assert_match "Knowledge Bus", shell_output("#{bin}/kb kbp --version")
    initialize = { jsonrpc: "2.0", id: 1, method: "initialize",
                   params: { protocolVersion: "2025-06-18", capabilities: {},
                             clientInfo: { name: "brew", version: "1" } } }
    assert_match '"name":"knowledge-mcp"', pipe_output("#{bin}/kb mcp", "#{JSON.generate(initialize)}\\n", 0)
  end
end
`;
}

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}
