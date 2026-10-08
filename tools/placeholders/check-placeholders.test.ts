import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const checker = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "check-placeholders.ts",
);

// Built at runtime, so this file holds no placeholder for the checker to find.
const ph = (name: string): string => `$${"{"}${name}}`;

const templateDoc = [
  "# Template",
  "",
  `| \`${ph("REPO_NAME")}\` | repo |`,
  `| \`${ph("BUNDLE_ID")}\` | app id |`,
  `| \`${ph("YEAR")}\` | year |`,
  `| \`${ph("COPYRIGHT_HOLDER")}\` | holder |`,
  "",
].join("\n");

function repo(files: Record<string, string>): string {
  const root = mkdtempSync(join(tmpdir(), "placeholders-"));
  for (const [path, contents] of Object.entries(files)) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), contents);
  }
  return root;
}

function run(root: string) {
  const result = spawnSync(process.execPath, [checker, root], {
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("template: passes when TEMPLATE.md lists every placeholder", () => {
  const { status, output } = run(
    repo({
      "TEMPLATE.md": templateDoc,
      "README.md": `# ${ph("REPO_NAME")}\n`,
      "app/conf.json": `{ "identifier": "${ph("BUNDLE_ID")}" }\n`,
      "licenses/MIT": `Copyright (c) ${ph("YEAR")} ${ph("COPYRIGHT_HOLDER")}\n`,
    }),
  );
  assert.equal(status, 0, output);
  assert.match(
    output,
    /template: 4 placeholders in 3 files, all listed in TEMPLATE\.md/,
  );
});

test("template: fails on a placeholder TEMPLATE.md does not list", () => {
  const { status, output } = run(
    repo({
      "TEMPLATE.md": templateDoc.replace(
        `| \`${ph("BUNDLE_ID")}\` | app id |\n`,
        "",
      ),
      "app/conf.json": `{ "identifier": "${ph("BUNDLE_ID")}" }\n`,
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /TEMPLATE\.md does not list \$\{BUNDLE_ID\}/);
});

test("template: fails on an unknown placeholder", () => {
  const { status, output } = run(
    repo({ "TEMPLATE.md": templateDoc, "README.md": `# ${ph("PRODUCT")}\n` }),
  );
  assert.equal(status, 1);
  assert.match(output, /README\.md:1: unknown placeholder \$\{PRODUCT\}/);
});

test("repo: fails on each placeholder left, with file and line", () => {
  const { status, output } = run(
    repo({
      LICENSE: "MIT\n",
      "README.md": `# Notes\n\n## What is ${ph("REPO_NAME")}?\n`,
      "app/conf.json": `{ "identifier": "${ph("BUNDLE_ID")}" }\n`,
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /README\.md:3: \$\{REPO_NAME\} is not filled in/);
  assert.match(output, /app\/conf\.json:1: \$\{BUNDLE_ID\} is not filled in/);
});

test("repo: fails while licenses/ remains or LICENSE is missing", () => {
  const { status, output } = run(repo({ "licenses/MIT": "MIT\n" }));
  assert.equal(status, 1);
  assert.match(output, /no LICENSE: copy one file from licenses\/ to LICENSE/);
  assert.match(
    output,
    /licenses\/ is still here: delete it once LICENSE is chosen/,
  );
});

test("repo: passes once everything is filled in", () => {
  const { status, output } = run(
    repo({ LICENSE: "MIT\n", "README.md": "# Notes\n" }),
  );
  assert.equal(status, 0, output);
  assert.match(output, /no placeholders left/);
});

test("ignores shell and GitHub expressions, dependencies and binary files", () => {
  const { status, output } = run(
    repo({
      LICENSE: "MIT\n",
      "ci.yml": "group: ci-$" + "{{ github.ref }}\n",
      "run.sh": `echo "${ph("HOME").toLowerCase()}"\n`,
      "node_modules/x/README.md": `${ph("REPO_NAME")}\n`,
      ".git/config": `${ph("REPO_NAME")}\n`,
      "icon.png": `\u0000${ph("REPO_NAME")}`,
    }),
  );
  assert.equal(status, 0, output);
});

test("repo: ignores an unlisted uppercase shell variable", () => {
  const { status, output } = run(
    repo({ LICENSE: "MIT\n", "run.sh": `echo "${ph("HOME")}"\n` }),
  );
  assert.equal(status, 0, output);
});
