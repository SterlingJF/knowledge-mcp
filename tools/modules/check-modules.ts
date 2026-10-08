#!/usr/bin/env node

// Checks that every module has a CI job, a check_<name> recipe run by `check`, a README, a README region,
// and, if it is a workspace package, a package name equal to its folder (pnpm --filter matches by name).
// A module is a workspace package, or a root folder whose README.md has a "## Layout" section.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";

import { parse } from "yaml";

const root = resolve(process.argv[2] ?? ".");
const failures: string[] = [];

const nodePackages = nodeModules();
const pythonPackages = pythonModules();
const modules = [
  ...new Set([...nodePackages, ...pythonPackages, ...layoutModules()]),
].sort();
const jobs = ciJobs();
const recipes = justRecipes();
const checkRuns = recipes.get("check") ?? [];
const regions = readmeRegions();

if (!jobs.includes("root")) failures.push('no CI job "root"');
if (!checkRuns.includes("check_root")) {
  failures.push('"check" does not run "check_root"');
}

for (const name of modules) {
  const recipe = `check_${name.replace(/-/g, "_")}`;
  if (!existsSync(join(root, name, "README.md"))) {
    failures.push(`${name}: no ${name}/README.md`);
  }
  if (!jobs.includes(name)) failures.push(`${name}: no CI job "${name}"`);
  if (!recipes.has(recipe)) failures.push(`${name}: no recipe "${recipe}"`);
  else if (!checkRuns.includes(recipe)) {
    failures.push(`${name}: "check" does not run "${recipe}"`);
  }
  if (!regions.includes(name)) {
    failures.push(`${name}: no README region "${name}/README.md#layout"`);
  }
}

for (const name of nodePackages) {
  const declared = packageName(
    name,
    "package.json",
    (text) => (JSON.parse(text) as { name?: unknown }).name,
  );
  if (declared !== undefined && declared !== name) {
    failures.push(`${name}: package.json name is "${declared}", not "${name}"`);
  }
}
for (const name of pythonPackages) {
  const declared = packageName(name, "pyproject.toml", (text) => {
    const project = text
      .split(/^\[/m)
      .find((table) => table.startsWith("project]"));
    return project && /^name\s*=\s*"([^"]+)"/m.exec(project)?.[1];
  });
  if (declared !== undefined && declared !== name) {
    failures.push(
      `${name}: pyproject.toml name is "${declared}", not "${name}"`,
    );
  }
}

for (const job of jobs) {
  if (job !== "root" && !modules.includes(job)) {
    failures.push(`CI job "${job}" matches no module`);
  }
}
const moduleRecipes = modules.map((name) => `check_${name.replace(/-/g, "_")}`);
for (const recipe of checkRuns) {
  if (recipe !== "check_root" && !moduleRecipes.includes(recipe)) {
    failures.push(`"check" runs "${recipe}", which matches no module`);
  }
}
for (const region of regions) {
  if (!modules.includes(region)) {
    failures.push(
      `README region "${region}/README.md#layout" matches no module`,
    );
  }
}

for (const failure of failures) console.error(failure);
console.log(
  `${modules.length} module${modules.length === 1 ? "" : "s"}: ${modules.join(", ")}`,
);
process.exitCode = failures.length === 0 ? 0 : 1;

function nodeModules(): string[] {
  const path = join(root, "pnpm-workspace.yaml");
  if (!existsSync(path)) return [];
  const workspace = parse(readFileSync(path, "utf8")) as {
    packages?: string[];
  };
  return workspace.packages ?? [];
}

function pythonModules(): string[] {
  const path = join(root, "pyproject.toml");
  if (!existsSync(path)) return [];
  const members = /^members\s*=\s*\[([^\]]*)\]/m.exec(
    readFileSync(path, "utf8"),
  );
  return members ? [...members[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]) : [];
}

function packageName(
  name: string,
  file: string,
  read: (text: string) => unknown,
): unknown {
  const path = join(root, name, file);
  if (!existsSync(path)) {
    failures.push(`${name}: no ${name}/${file}`);
    return undefined;
  }
  const declared = read(readFileSync(path, "utf8"));
  if (declared === undefined || declared === "") {
    failures.push(`${name}: ${file} declares no name`);
  }
  return declared || undefined;
}

function layoutModules(): string[] {
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => {
      const readme = join(root, name, "README.md");
      return (
        existsSync(readme) && /^## Layout$/m.test(readFileSync(readme, "utf8"))
      );
    });
}

function ciJobs(): string[] {
  const path = join(root, ".github/workflows/ci.yml");
  if (!existsSync(path)) return [];
  const workflow = parse(readFileSync(path, "utf8")) as {
    jobs?: Record<string, unknown>;
  };
  return Object.keys(workflow.jobs ?? {});
}

function justRecipes(): Map<string, string[]> {
  const recipes = new Map<string, string[]>();
  for (const line of readFileSync(join(root, "justfile"), "utf8").split("\n")) {
    const match = /^([A-Za-z_][\w-]*)(?:\s+[^:=]*)?:(?!=)(.*)$/.exec(line);
    if (match)
      recipes.set(match[1], match[2].trim().split(/\s+/).filter(Boolean));
  }
  return recipes;
}

function readmeRegions(): string[] {
  const readme = readFileSync(join(root, "README.md"), "utf8");
  return [
    ...readme.matchAll(
      /<!-- BEGIN AUTO-GENERATED ([^/\s]+)\/README\.md#layout -->/g,
    ),
  ].map((match) => match[1]);
}
