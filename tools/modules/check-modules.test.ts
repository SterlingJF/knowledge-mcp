import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "check-modules.ts",
);

type Repo = {
  node?: string[];
  python?: string[];
  data?: string[];
  packageNames?: Record<string, string>;
  jobs?: string[];
  recipes?: string[];
  check?: string[];
  regions?: string[];
  readmes?: string[];
};

function repo(spec: Repo = {}): string {
  const node = spec.node ?? ["web-app"];
  const python = spec.python ?? ["api-app"];
  const data = spec.data ?? [];
  const modules = [...node, ...python, ...data];
  const jobs = spec.jobs ?? ["root", ...modules];
  const recipes =
    spec.recipes ?? modules.map((name) => `check_${name.replace(/-/g, "_")}`);
  const check = spec.check ?? ["check_root", ...recipes];
  const regions = spec.regions ?? modules;
  const readmes = spec.readmes ?? modules;

  const dir = mkdtempSync(join(tmpdir(), "modules-"));
  const write = (path: string, text: string): void => {
    mkdirSync(dirname(join(dir, path)), { recursive: true });
    writeFileSync(join(dir, path), text);
  };
  write(
    "pnpm-workspace.yaml",
    `---\npackages:\n${node.map((name) => `  - ${name}\n`).join("")}`,
  );
  write(
    "pyproject.toml",
    `[tool.uv.workspace]\nmembers = [${python.map((name) => `"${name}"`).join(", ")}]\n`,
  );
  write(
    ".github/workflows/ci.yml",
    `---\nname: CI\njobs:\n${jobs.map((name) => `  ${name}:\n    runs-on: ubuntu-latest\n`).join("")}`,
  );
  write(
    "justfile",
    [
      `check: ${check.join(" ")}`,
      "",
      "check_root:",
      "  true",
      ...recipes.flatMap((name) => ["", `${name}:`, "  true"]),
      "",
    ].join("\n"),
  );
  write(
    "README.md",
    regions
      .map(
        (name) =>
          `<!-- BEGIN AUTO-GENERATED ${name}/README.md#layout -->\n<!-- END AUTO-GENERATED ${name}/README.md#layout -->\n`,
      )
      .join("\n"),
  );
  for (const name of node) {
    const packageName = spec.packageNames?.[name] ?? name;
    write(`${name}/package.json`, `${JSON.stringify({ name: packageName })}\n`);
  }
  for (const name of python) {
    const packageName = spec.packageNames?.[name] ?? name;
    write(
      `${name}/pyproject.toml`,
      `[project]\nname = "${packageName}"\nversion = "0.1.0"\n`,
    );
  }
  for (const name of readmes) {
    const layout = data.includes(name) ? "\n## Layout\n" : "";
    write(`${name}/README.md`, `# ${name}\n${layout}`);
  }
  return dir;
}

function run(dir: string) {
  const result = spawnSync(process.execPath, [script, dir], {
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

test("passes when every module is wired the same way", () => {
  const { status, output } = run(repo());
  assert.equal(status, 0, output);
  assert.match(output, /2 modules: api-app, web-app/);
});

test("fails when a module has no CI job", () => {
  const { status, output } = run(repo({ jobs: ["root", "web-app"] }));
  assert.equal(status, 1);
  assert.match(output, /api-app: no CI job "api-app"/);
});

test("fails when a module has no check recipe", () => {
  const { status, output } = run(repo({ recipes: ["check_web_app"] }));
  assert.equal(status, 1);
  assert.match(output, /api-app: no recipe "check_api_app"/);
});

test("fails when check does not run a module recipe", () => {
  const { status, output } = run(
    repo({ check: ["check_root", "check_web_app"] }),
  );
  assert.equal(status, 1);
  assert.match(output, /api-app: "check" does not run "check_api_app"/);
});

test("fails when check does not run check_root", () => {
  const { status, output } = run(
    repo({ check: ["check_web_app", "check_api_app"] }),
  );
  assert.equal(status, 1);
  assert.match(output, /"check" does not run "check_root"/);
});

test("fails when a module has no README region", () => {
  const { status, output } = run(repo({ regions: ["web-app"] }));
  assert.equal(status, 1);
  assert.match(
    output,
    /api-app: no README region "api-app\/README\.md#layout"/,
  );
});

test("fails when a module has no README", () => {
  const { status, output } = run(repo({ readmes: ["web-app"] }));
  assert.equal(status, 1);
  assert.match(output, /api-app: no api-app\/README\.md/);
});

test("fails on a CI job that matches no module", () => {
  const { status, output } = run(
    repo({ jobs: ["root", "web-app", "api-app", "old-app"] }),
  );
  assert.equal(status, 1);
  assert.match(output, /CI job "old-app" matches no module/);
});

test("fails on a README region that matches no module", () => {
  const { status, output } = run(
    repo({ regions: ["web-app", "api-app", "old-app"] }),
  );
  assert.equal(status, 1);
  assert.match(
    output,
    /README region "old-app\/README\.md#layout" matches no module/,
  );
});

test("fails when the root CI job is missing", () => {
  const { status, output } = run(repo({ jobs: ["web-app", "api-app"] }));
  assert.equal(status, 1);
  assert.match(output, /no CI job "root"/);
});

test("fails when check runs a recipe that matches no module", () => {
  const { status, output } = run(
    repo({
      check: ["check_root", "check_web_app", "check_api_app", "check_old_app"],
    }),
  );
  assert.equal(status, 1);
  assert.match(output, /"check" runs "check_old_app", which matches no module/);
});

test("passes with no Python modules", () => {
  const { status, output } = run(repo({ python: [] }));
  assert.equal(status, 0, output);
  assert.match(output, /1 module: web-app/);
});

test("counts a root folder whose README has a Layout section as a module", () => {
  const { status, output } = run(repo({ data: ["evals"] }));
  assert.equal(status, 0, output);
  assert.match(output, /3 modules: api-app, evals, web-app/);
});

test("fails when a data-only module has no CI job", () => {
  const { status, output } = run(
    repo({ data: ["evals"], jobs: ["root", "web-app", "api-app"] }),
  );
  assert.equal(status, 1);
  assert.match(output, /evals: no CI job "evals"/);
});

test("ignores a root folder whose README has no Layout section", () => {
  const dir = repo();
  mkdirSync(join(dir, ".evidence"));
  writeFileSync(join(dir, ".evidence/README.md"), "# Evidence\n");
  const { status, output } = run(dir);
  assert.equal(status, 0, output);
  assert.match(output, /2 modules: api-app, web-app/);
});

test("fails when a Node module's package name differs from its folder", () => {
  const { status, output } = run(repo({ packageNames: { "web-app": "web" } }));
  assert.equal(status, 1);
  assert.match(output, /web-app: package\.json name is "web", not "web-app"/);
});

test("fails when a Python module's project name differs from its folder", () => {
  const { status, output } = run(repo({ packageNames: { "api-app": "api" } }));
  assert.equal(status, 1);
  assert.match(output, /api-app: pyproject\.toml name is "api", not "api-app"/);
});
