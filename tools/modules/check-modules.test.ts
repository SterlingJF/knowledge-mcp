import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "check-modules.ts",
);

type Repo = {
  node?: Array<string>;
  python?: Array<string>;
  data?: Array<string>;
  packageNames?: Record<string, string>;
  jobs?: Array<string>;
  recipes?: Array<string>;
  check?: Array<string>;
  regions?: Array<string>;
  readmes?: Array<string>;
  root?: Array<string>;
};

interface Wiring {
  node: Array<string>;
  python: Array<string>;
  data: Array<string>;
  jobs: Array<string>;
  recipes: Array<string>;
  check: Array<string>;
  regions: Array<string>;
  readmes: Array<string>;
}

function wiring(spec: Repo): Wiring {
  const node = spec.node ?? ["web-app"];
  const python = spec.python ?? ["api-app"];
  const data = spec.data ?? [];
  const modules = [...node, ...python, ...data];
  const recipes =
    spec.recipes ?? modules.map((name) => `check_${name.replace(/-/g, "_")}`);
  return {
    node,
    python,
    data,
    jobs: spec.jobs ?? ["root", ...modules],
    recipes,
    check: spec.check ?? ["check_root", ...recipes],
    regions: spec.regions ?? modules,
    readmes: spec.readmes ?? modules,
  };
}

function writeRootFiles(
  write: (path: string, text: string) => void,
  wired: Wiring,
  rootNames: Array<string>,
): void {
  write(
    "pnpm-workspace.yaml",
    `---\npackages:\n${wired.node.map((name) => `  - ${name}\n`).join("")}`,
  );
  write(
    "pyproject.toml",
    `[tool.uv.workspace]\nmembers = [${wired.python.map((name) => `"${name}"`).join(", ")}]\n`,
  );
  write(
    ".github/workflows/ci.yml",
    `---\nname: CI\njobs:\n${wired.jobs.map((name) => `  ${name}:\n    runs-on: ubuntu-latest\n`).join("")}`,
  );
  write(
    "justfile",
    [
      `check: ${wired.check.join(" ")}`,
      "",
      "check_root:",
      "  true",
      ...wired.recipes.flatMap((name) => ["", `${name}:`, "  true"]),
      "",
    ].join("\n"),
  );
  write(
    "CONTRIBUTING.md",
    "### Root\n\n```text\n.\n" +
      rootNames.map((name) => `├── ${name}/`).join("\n") +
      "\n```\n\n" +
      wired.regions
        .map(
          (name) =>
            `<!-- BEGIN AUTO-GENERATED ${name}/README.md#layout -->\n<!-- END AUTO-GENERATED ${name}/README.md#layout -->\n`,
        )
        .join("\n"),
  );
}

function writeModuleFiles(
  write: (path: string, text: string) => void,
  wired: Wiring,
  packageNames: Record<string, string> = {},
): void {
  for (const name of wired.node) {
    const packageName = packageNames[name] ?? name;
    write(`${name}/package.json`, `${JSON.stringify({ name: packageName })}\n`);
  }
  for (const name of wired.python) {
    const packageName = packageNames[name] ?? name;
    write(
      `${name}/pyproject.toml`,
      `[project]\nname = "${packageName}"\nversion = "0.1.0"\n`,
    );
  }
  for (const name of wired.readmes) {
    const layout = wired.data.includes(name) ? "\n## Layout\n" : "";
    write(`${name}/README.md`, `# ${name}\n${layout}`);
  }
}

function repo(spec: Repo = {}): string {
  const wired = wiring(spec);
  const dir = mkdtempSync(join(tmpdir(), "modules-"));
  const write = (path: string, text: string): void => {
    mkdirSync(dirname(join(dir, path)), { recursive: true });
    writeFileSync(join(dir, path), text);
  };
  writeRootFiles(
    write,
    wired,
    spec.root ?? [".github", ...wired.node, ...wired.python, ...wired.data],
  );
  writeModuleFiles(write, wired, spec.packageNames);
  return dir;
}

function run(dir: string) {
  const result = spawnSync(process.execPath, [script, dir], {
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("passes when every module has a README, a CI job, a check recipe and a map region", () => {
  const { status, output } = run(repo());
  assert.equal(status, 0, output);
  assert.match(output, /2 modules: api-app, web-app/);
});

test("fails when a module has no CI job", () => {
  const { status, output } = run(repo({ jobs: ["root", "web-app"] }));
  assert.equal(status, 1);
  assert.match(
    output,
    /api-app: add a job named api-app to \.github\/workflows\/ci\.yml\./,
  );
});

test("fails when a module has no check recipe", () => {
  const { status, output } = run(repo({ recipes: ["check_web_app"] }));
  assert.equal(status, 1);
  assert.match(output, /api-app: add a check_api_app recipe to the justfile\./);
});

test("fails when the check recipe does not run a module recipe", () => {
  const { status, output } = run(
    repo({ check: ["check_root", "check_web_app"] }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /api-app: add check_api_app to the check recipe in the justfile\./,
  );
});

test("fails when the check recipe does not run check_root", () => {
  const { status, output } = run(
    repo({ check: ["check_web_app", "check_api_app"] }),
  );
  assert.equal(status, 1);
  assert.match(output, /add check_root to the check recipe in the justfile\./);
});

test("fails when CONTRIBUTING.md has no map region for a module", () => {
  const { status, output } = run(repo({ regions: ["web-app"] }));
  assert.equal(status, 1);
  assert.match(
    output,
    /api-app: add <!-- BEGIN AUTO-GENERATED api-app\/README\.md#layout --> and the matching END marker to CONTRIBUTING\.md\. Run `just generate_readme_maps`\./,
  );
});

test("fails when a module has no README", () => {
  const { status, output } = run(repo({ readmes: ["web-app"] }));
  assert.equal(status, 1);
  assert.match(output, /api-app: add api-app\/README\.md\./);
});

test("fails on a CI job that matches no module", () => {
  const { status, output } = run(
    repo({ jobs: ["root", "web-app", "api-app", "old-app"] }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /CI job old-app matches no module: rename the job, or delete the job from \.github\/workflows\/ci\.yml\./,
  );
});

test("fails on a CONTRIBUTING.md map region that matches no module", () => {
  const { status, output } = run(
    repo({ regions: ["web-app", "api-app", "old-app"] }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /CONTRIBUTING\.md region old-app\/README\.md#layout matches no module: delete the region from CONTRIBUTING\.md\./,
  );
});

test("fails when the root CI job is missing", () => {
  const { status, output } = run(repo({ jobs: ["web-app", "api-app"] }));
  assert.equal(status, 1);
  assert.match(
    output,
    /add a job named root to \.github\/workflows\/ci\.yml\./,
  );
});

test("fails when the check recipe runs a recipe that matches no module", () => {
  const { status, output } = run(
    repo({
      check: ["check_root", "check_web_app", "check_api_app", "check_old_app"],
    }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /the check recipe runs check_old_app, which matches no module: delete check_old_app from the check recipe in the justfile\./,
  );
});

test("passes with no Python modules", () => {
  const { status, output } = run(repo({ python: [] }));
  assert.equal(status, 0, output);
  assert.match(output, /1 module: web-app/);
});

test("counts a top-level folder whose README has a Layout section as a module", () => {
  const { status, output } = run(repo({ data: ["evals"] }));
  assert.equal(status, 0, output);
  assert.match(output, /3 modules: api-app, evals, web-app/);
});

test("fails when a top-level folder with a Layout section has no CI job", () => {
  const { status, output } = run(
    repo({ data: ["evals"], jobs: ["root", "web-app", "api-app"] }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /evals: add a job named evals to \.github\/workflows\/ci\.yml\./,
  );
});

test("ignores a top-level folder whose README has no Layout section", () => {
  const dir = repo({ root: [".github", "api-app", "web-app", ".evidence"] });
  mkdirSync(join(dir, ".evidence"));
  writeFileSync(join(dir, ".evidence/README.md"), "# Evidence\n");
  const { status, output } = run(dir);
  assert.equal(status, 0, output);
  assert.match(output, /2 modules: api-app, web-app/);
});

test("fails when a Node package name differs from its folder name", () => {
  const { status, output } = run(repo({ packageNames: { "web-app": "web" } }));
  assert.equal(status, 1);
  assert.match(
    output,
    /web-app: web-app\/package\.json names the package web\. Set the name to web-app\./,
  );
});

test("passes when the runtime module keeps its knowledge-mcp distribution name", () => {
  const { status, output } = run(
    repo({ python: ["runtime"], packageNames: { runtime: "knowledge-mcp" } }),
  );
  assert.equal(status, 0, output);
  assert.match(output, /2 modules: runtime, web-app/);
});

test("fails when a Python module declares no project name", () => {
  const dir = repo();
  writeFileSync(
    join(dir, "api-app/pyproject.toml"),
    '[project]\nversion = "0.1.0"\n',
  );
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /api-app: add a name to api-app\/pyproject\.toml\./);
});

test("fails when a Python module's project name is empty or whitespace", () => {
  for (const name of ["", "   "]) {
    const { status, output } = run(repo({ packageNames: { "api-app": name } }));
    assert.equal(status, 1, output);
    assert.match(output, /api-app: add a name to api-app\/pyproject\.toml\./);
  }
});

function rootTree(dir: string, tree: string): void {
  const path = join(dir, "CONTRIBUTING.md");
  writeFileSync(
    path,
    readFileSync(path, "utf8").replace(
      /```text[\s\S]*?```/u,
      "```text\n.\n" + tree + "\n```",
    ),
  );
}

for (const [name, tree, expected] of [
  [
    "missing root path",
    "├── .github/\n├── api-app/\n├── web-app/\n└── skills/",
    "skills/ does not exist",
  ],
  [
    "missing top-level folder",
    "├── api-app/\n└── web-app/",
    "no line for .github/",
  ],
  [
    "file marked as folder",
    "├── .github/\n├── api-app/\n├── web-app/\n└── justfile/",
    "justfile is a file",
  ],
  [
    "unmatched pattern",
    "├── .github/\n├── api-app/\n├── web-app/\n└── *.schema.yaml",
    "nothing matches *.schema.yaml",
  ],
  [
    "placeholder",
    "├── .github/\n├── api-app/\n├── web-app/\n└── <name>.schema.yaml",
    "contains a placeholder",
  ],
  [
    "several names",
    "├── .github/, .agents/\n├── api-app/\n└── web-app/",
    ".agents/ does not exist",
  ],
] as const) {
  test(`fails on ${name} in a map`, () => {
    const dir = repo();
    rootTree(dir, tree);
    const result = run(dir);
    assert.equal(result.status, 1, result.output);
    assert.ok(result.output.includes(expected), result.output);
  });
}

test("fails when a module map names a missing path", () => {
  const dir = repo({ data: ["evals"] });
  writeFileSync(
    join(dir, "evals/README.md"),
    "# evals\n\n## Layout\n\n```text\nevals/\n└── old.py\n```\n",
  );
  const result = run(dir);
  assert.equal(result.status, 1, result.output);
  assert.ok(
    result.output.includes("evals/old.py does not exist"),
    result.output,
  );
});

test("fails when CONTRIBUTING.md has no root map", () => {
  const dir = repo();
  writeFileSync(
    join(dir, "CONTRIBUTING.md"),
    readFileSync(join(dir, "CONTRIBUTING.md"), "utf8").replace(
      /### Root[\s\S]*?```\n\n/u,
      "",
    ),
  );
  const result = run(dir);
  assert.equal(result.status, 1);
  assert.ok(result.output.includes("no root map"), result.output);
});

test("passes with patterns, nested paths, several names on one line and a ... line", () => {
  const dir = repo();
  rootTree(
    dir,
    "├── .github/workflows/\n│   └── *.yml # pattern\n├── api-app/, web-app/\n└── ...",
  );
  const result = run(dir);
  assert.equal(result.status, 0, result.output);
});

test("passes when extra folders hold only ignored files or are empty", () => {
  const dir = repo();
  for (const folder of ["server/dist", "node_modules/x", "components", ".git"])
    mkdirSync(join(dir, folder), { recursive: true });
  writeFileSync(join(dir, "server/dist/km-server"), "binary");
  writeFileSync(join(dir, "node_modules/x/index.js"), "export {};");
  writeFileSync(join(dir, ".gitignore"), "dist/\nnode_modules/\n");
  const result = run(dir);
  assert.equal(result.status, 0, result.output);
});
