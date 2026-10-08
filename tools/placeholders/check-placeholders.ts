#!/usr/bin/env node

// In the template (TEMPLATE.md present): checks TEMPLATE.md lists every placeholder in use.
// In a repo made from it: fails on any placeholder left, and until one license is chosen.

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";

// Every placeholder the template uses. Add one here and to TEMPLATE.md.
const placeholders = ["REPO_NAME", "BUNDLE_ID", "YEAR", "COPYRIGHT_HOLDER"];

// Not authored here: dependencies, build output, VCS data, local evidence.
const skipped = new Set([
  ".git",
  ".evidence",
  ".venv",
  "node_modules",
  "target",
  "dist",
]);

const root = resolve(process.argv[2] ?? ".");
const isTemplate = existsSync(join(root, "TEMPLATE.md"));
const failures: string[] = [];
const used = new Set<string>();
const files = new Set<string>();

for (const path of walk(root)) {
  const text = readFileSync(path, "utf8");
  if (text.includes("\u0000")) continue;
  const label = relative(root, path).split(sep).join("/");
  if (isTemplate && label === "TEMPLATE.md") continue;
  text.split("\n").forEach((line, index) => {
    for (const [, name] of line.matchAll(/\$\{([A-Z][A-Z0-9_]*)\}/g)) {
      const where = `${label}:${index + 1}`;
      if (!placeholders.includes(name)) {
        if (isTemplate)
          failures.push(`${where}: unknown placeholder \${${name}}`);
        continue;
      }
      used.add(name);
      files.add(label);
      if (!isTemplate) failures.push(`${where}: \${${name}} is not filled in`);
    }
  });
}

if (isTemplate) {
  const listed = readFileSync(join(root, "TEMPLATE.md"), "utf8");
  for (const name of used) {
    if (!listed.includes(`\${${name}}`)) {
      failures.push(`TEMPLATE.md does not list \${${name}}`);
    }
  }
} else {
  if (!existsSync(join(root, "LICENSE"))) {
    failures.push("no LICENSE: copy one file from licenses/ to LICENSE");
  }
  if (existsSync(join(root, "licenses"))) {
    failures.push("licenses/ is still here: delete it once LICENSE is chosen");
  }
}

for (const failure of failures) console.error(failure);
if (failures.length === 0) {
  console.log(
    isTemplate
      ? `template: ${used.size} placeholders in ${files.size} files, all listed in TEMPLATE.md`
      : "no placeholders left",
  );
}
process.exitCode = failures.length === 0 ? 0 : 1;

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (skipped.has(entry.name)) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.isFile()) yield path;
  }
}
