#!/usr/bin/env node

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

import ignore from "ignore";
import { parse } from "yaml";

type Rules = ReturnType<typeof ignore>;
const branch = /^((?:│ {3}| {4})*)[├└]── (.+?)(?: +#.*)?$/u;

const root = resolve(process.argv[2] ?? ".");
const failures: Array<string> = [];

const nodePackages = nodeModules();
const pythonPackages = pythonModules();
const modules = [
  ...new Set([...nodePackages, ...pythonPackages, ...layoutModules()]),
].sort();
const jobs = ciJobs();
const recipes = justRecipes();
const checkRuns = recipes.get("check") ?? [];
const regions = readmeRegions();

if (!jobs.includes("root")) {
  failures.push("add a job named root to .github/workflows/ci.yml.");
}
if (!checkRuns.includes("check_root")) {
  failures.push("add check_root to the check recipe in the justfile.");
}

for (const name of modules) {
  const recipe = `check_${name.replace(/-/g, "_")}`;
  if (!existsSync(join(root, name, "README.md"))) {
    failures.push(`${name}: add ${name}/README.md.`);
  }
  if (!jobs.includes(name)) {
    failures.push(
      `${name}: add a job named ${name} to .github/workflows/ci.yml.`,
    );
  }
  if (!recipes.has(recipe)) {
    failures.push(`${name}: add a ${recipe} recipe to the justfile.`);
  } else if (!checkRuns.includes(recipe)) {
    failures.push(
      `${name}: add ${recipe} to the check recipe in the justfile.`,
    );
  }
  if (!regions.includes(name)) {
    failures.push(
      `${name}: add <!-- BEGIN AUTO-GENERATED ${name}/README.md#layout --> and the matching END marker to CONTRIBUTING.md. Run \`just generate_readme_maps\`.`,
    );
  }
}

for (const name of nodePackages) {
  const declared = packageName(name, "package.json", (text) => {
    const manifest: unknown = JSON.parse(text);
    return isObject(manifest) &&
      "name" in manifest &&
      typeof manifest.name === "string"
      ? manifest.name
      : undefined;
  });
  if (declared !== undefined && declared !== name) {
    failures.push(
      `${name}: ${name}/package.json names the package ${declared}. Set the name to ${name}.`,
    );
  }
}
for (const name of pythonPackages) {
  packageName(name, "pyproject.toml", (text) => {
    const project = text
      .split(/^\[/m)
      .find((table) => table.startsWith("project]"));
    return project && /^name\s*=\s*"([^"]+)"/m.exec(project)?.[1];
  });
}

for (const job of jobs) {
  if (job !== "root" && !modules.includes(job)) {
    failures.push(
      `CI job ${job} matches no module: rename the job, or delete the job from .github/workflows/ci.yml.`,
    );
  }
}
const moduleRecipes = modules.map((name) => `check_${name.replace(/-/g, "_")}`);
for (const recipe of checkRuns) {
  if (recipe !== "check_root" && !moduleRecipes.includes(recipe)) {
    failures.push(
      `the check recipe runs ${recipe}, which matches no module: delete ${recipe} from the check recipe in the justfile.`,
    );
  }
}
for (const region of regions) {
  if (!modules.includes(region)) {
    failures.push(
      `CONTRIBUTING.md region ${region}/README.md#layout matches no module: delete the region from CONTRIBUTING.md.`,
    );
  }
}

checkMaps();

for (const failure of failures) console.error(failure);
console.log(
  `${modules.length} module${modules.length === 1 ? "" : "s"}: ${modules.join(", ")}`,
);
process.exitCode = failures.length === 0 ? 0 : 1;

function nodeModules(): Array<string> {
  const path = join(root, "pnpm-workspace.yaml");
  if (!existsSync(path)) return [];
  const workspace: unknown = parse(readFileSync(path, "utf8"));
  return isObject(workspace) &&
    "packages" in workspace &&
    isStrings(workspace.packages)
    ? workspace.packages
    : [];
}

function pythonModules(): Array<string> {
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
  read: (text: string) => string | undefined,
): string | undefined {
  const path = join(root, name, file);
  if (!existsSync(path)) {
    failures.push(`${name}: add ${name}/${file}.`);
    return undefined;
  }
  const declared = read(readFileSync(path, "utf8"));
  if (declared === undefined || declared.trim() === "") {
    failures.push(`${name}: add a name to ${name}/${file}.`);
    return undefined;
  }
  return declared;
}

function layoutModules(): Array<string> {
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== ".git")
    .map((entry) => entry.name)
    .filter((name) => {
      const readme = join(root, name, "README.md");
      return (
        existsSync(readme) && /^## Layout$/m.test(readFileSync(readme, "utf8"))
      );
    });
}

function ciJobs(): Array<string> {
  const path = join(root, ".github/workflows/ci.yml");
  if (!existsSync(path)) return [];
  const workflow: unknown = parse(readFileSync(path, "utf8"));
  return isObject(workflow) && "jobs" in workflow && isObject(workflow.jobs)
    ? Object.keys(workflow.jobs)
    : [];
}

function justRecipes(): Map<string, Array<string>> {
  const found = new Map<string, Array<string>>();
  for (const line of readFileSync(join(root, "justfile"), "utf8").split("\n")) {
    const match = /^([A-Za-z_][\w-]*)(?:\s+[^:=]*)?:(?!=)(.*)$/.exec(line);
    if (match)
      found.set(match[1], match[2].trim().split(/\s+/).filter(Boolean));
  }
  return found;
}

function readmeRegions(): Array<string> {
  const readme = readFileSync(join(root, "CONTRIBUTING.md"), "utf8");
  return [
    ...readme.matchAll(
      /<!-- BEGIN AUTO-GENERATED ([^/\s]+)\/README\.md#layout -->/g,
    ),
  ].map((match) => match[1]);
}

function isObject(value: unknown): value is object {
  return typeof value === "object" && value !== null;
}

function isStrings(value: unknown): value is Array<string> {
  return (
    Array.isArray(value) && value.every((item) => typeof item === "string")
  );
}

function checkMaps(): void {
  const rootMap = textBlock(
    readFileSync(join(root, "CONTRIBUTING.md"), "utf8"),
    "### Root",
  );
  if (rootMap === undefined) {
    failures.push(
      'CONTRIBUTING.md: no root map. Add a text block under "### Root".',
    );
  } else {
    const listed = checkTree("CONTRIBUTING.md#root", rootMap);
    for (const folder of trackedFolders()) {
      if (!listed.has(folder)) {
        failures.push(
          `CONTRIBUTING.md#root: no line for ${folder}/. Add the folder to the root map, or ignore the folder in .gitignore.`,
        );
      }
    }
  }
  for (const name of modules) {
    const readme = join(root, name, "README.md");
    if (!existsSync(readme)) continue;
    const tree = textBlock(readFileSync(readme, "utf8"), "## Layout");
    if (tree !== undefined) checkTree(`${name}/README.md#layout`, tree);
  }
}

function textBlock(text: string, heading: string): Array<string> | undefined {
  const lines = text.split("\n");
  const start = lines.indexOf(heading);
  if (start === -1) return undefined;
  const level = heading.indexOf(" ");
  const block: Array<string> = [];
  let inside = false;
  for (const line of lines.slice(start + 1)) {
    if (inside) {
      if (line === "```") return block;
      if (line.trim() !== "") block.push(line);
    } else if (line === "```text") {
      inside = true;
    } else if (/^#{1,6} /.test(line) && line.indexOf(" ") <= level) {
      return undefined;
    }
  }
  return undefined;
}

/** Reports invalid tree lines and paths; returns top-level names for coverage checks. */
function checkTree(source: string, lines: Array<string>): Set<string> {
  const top = new Set<string>();
  const base = lines[0] === "." ? "" : lines[0].replace(/\/$/, "");
  const parents = [base];
  for (const line of lines.slice(1)) {
    const match = branch.exec(line);
    if (!match) {
      failures.push(
        `${source}: "${line.trim()}" is not a tree line. Start the line with ├── or └──.`,
      );
      continue;
    }
    const depth = match[1].length / 4;
    const parent = parents[depth] ?? base;
    let last = parent;
    for (const name of match[2].split(", ")) {
      if (name === "...") continue;
      const path = [parent, name.replace(/\/$/, "")].filter(Boolean).join("/");
      if (depth === 0) top.add(name.split("/")[0]);
      checkPath(source, path, name.endsWith("/"));
      last = path;
    }
    parents.length = depth + 1;
    parents.push(last);
  }
  return top;
}

function checkPath(source: string, path: string, folder: boolean): void {
  const shown = folder ? `${path}/` : path;
  const name = path.split("/").at(-1) ?? path;
  if (/[<>]/.test(path)) {
    failures.push(
      `${source}: ${shown} contains a placeholder. Name a real path, or use * in a pattern.`,
    );
  } else if (name.includes("*")) {
    const dir = join(root, path, "..");
    const pattern = new RegExp(`^${name.split("*").map(literal).join(".*")}$`);
    if (
      !existsSync(dir) ||
      !readdirSync(dir).some((entry) => pattern.test(entry))
    ) {
      failures.push(
        `${source}: nothing matches ${shown}. Fix the pattern or drop the line.`,
      );
    }
  } else if (!existsSync(join(root, path))) {
    failures.push(
      `${source}: ${shown} does not exist. Fix the map line or restore the path.`,
    );
  } else if (statSync(join(root, path)).isDirectory() !== folder) {
    failures.push(
      folder
        ? `${source}: ${path} is a file. Drop the trailing / from the map line.`
        : `${source}: ${path} is a folder. End the name with / in the map line.`,
    );
  }
}

function literal(text: string): string {
  return text.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
}

function trackedFolders(): Array<string> {
  const path = join(root, ".gitignore");
  const rules = ignore().add(
    existsSync(path) ? readFileSync(path, "utf8") : "",
  );
  return readdirSync(root, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name !== ".git")
    .map((entry) => entry.name)
    .filter(
      (name) => !rules.ignores(`${name}/`) && holdsTrackedFile(rules, name),
    );
}

function holdsTrackedFile(rules: Rules, folder: string): boolean {
  for (const entry of readdirSync(join(root, folder), {
    withFileTypes: true,
  })) {
    if (entry.name === ".git" || entry.name === "WORKING_NOTES.md") continue;
    const path = `${folder}/${entry.name}`;
    if (
      entry.isDirectory()
        ? !rules.ignores(`${path}/`) && holdsTrackedFile(rules, path)
        : !rules.ignores(path)
    ) {
      return true;
    }
  }
  return false;
}
