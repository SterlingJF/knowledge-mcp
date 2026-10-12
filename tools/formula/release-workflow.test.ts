import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

interface Step {
  name?: string;
  run?: string;
  uses?: string;
  id?: string;
  if?: string;
  "continue-on-error"?: boolean;
  with?: Record<string, unknown>;
  env?: Record<string, string>;
}
interface Job {
  needs?: string | Array<string>;
  if?: string;
  "continue-on-error"?: boolean;
  permissions?: Record<string, string>;
  steps: Array<Step>;
  strategy?: {
    matrix?: {
      include?: Array<{
        runner: string;
        arch: string;
        prefix: string;
        bottle_tag: string;
      }>;
    };
  };
  outputs?: Record<string, string>;
}
const workflow = parse(
  readFileSync(
    new URL("../../.github/workflows/release.yml", import.meta.url),
    "utf8",
  ),
) as {
  jobs: Record<string, Job>;
  permissions?: Record<string, string>;
  on: {
    workflow_dispatch: {
      inputs: {
        tag: { required: boolean; type: string; default?: unknown };
      };
    };
  };
};
const root = fileURLToPath(new URL("../../", import.meta.url));

function dryRun(recipe: string, args: Array<string> = []): string {
  const result = spawnSync("just", ["--dry-run", recipe, ...args], {
    cwd: root,
    encoding: "utf8",
  });
  const output = (result.stdout + result.stderr).trim();
  assert.equal(result.status, 0, output);
  return output;
}

function needs(job: Job): Array<string> {
  return typeof job.needs === "string" ? [job.needs] : (job.needs ?? []);
}

test("manual bottle releases require an explicit tag without a preset version", () => {
  const tag = workflow.on.workflow_dispatch.inputs.tag;
  assert.equal(tag.required, true, "manual dispatch requires a release tag");
  assert.equal(tag.type, "string", "manual dispatch accepts a tag string");
  assert.equal(
    Object.hasOwn(tag, "default"),
    false,
    "manual dispatch must not preselect an old release",
  );
});

test("release jobs call cohesive root recipes instead of embedding programs", () => {
  const cases: Array<[string, string, Array<string>, string]> = [
    [
      "source",
      "release_target",
      ["v0.2.0", "SterlingJF/knowledge-mcp"],
      "target --tag 'v0.2.0' --repo 'SterlingJF/knowledge-mcp'",
    ],
    [
      "source",
      "release_source",
      ["tagged source"],
      "source --release dist/release.json --source 'tagged source'",
    ],
    [
      "bottles",
      "release_bottle",
      ["arm64", "/opt/homebrew", "arm64_sequoia"],
      "bottle --release dist/release.json --arch 'arm64' --prefix '/opt/homebrew' --bottle-tag 'arm64_sequoia'",
    ],
    [
      "release-bottles",
      "release_merge",
      [],
      "merge --release dist/release.json",
    ],
    [
      "verify-installs",
      "release_verify",
      ["x86_64", "/usr/local", "sequoia"],
      "verify --release dist/release.json --arch 'x86_64' --prefix '/usr/local' --bottle-tag 'sequoia'",
    ],
    [
      "tap",
      "release_tap",
      ["tap with spaces"],
      "tap --release dist/release.json --tap 'tap with spaces'",
    ],
  ];
  for (const [job, recipe, args, expected] of cases) {
    assert.equal(
      dryRun(recipe, args),
      `node tools/formula/release.ts ${expected}`,
    );
    assert.ok(
      workflow.jobs[job].steps.some((step) =>
        step.run?.startsWith(`just ${recipe}`),
      ),
      `${job} invokes ${recipe}`,
    );
  }
  for (const job of Object.values(workflow.jobs)) {
    for (const step of job.steps)
      if (step.run) {
        assert.equal(
          step.run.trim().split("\n").length,
          1,
          "workflow run steps contain one named command",
        );
        assert.doesNotMatch(step.run, /python|<<|\.sh|published-bottles/);
      }
  }
});

test("the entire native build and validation matrices gate the tap", () => {
  assert.deepEqual(needs(workflow.jobs.bottles), ["source"]);
  assert.deepEqual(needs(workflow.jobs["release-bottles"]), [
    "source",
    "bottles",
  ]);
  assert.deepEqual(needs(workflow.jobs["verify-installs"]), [
    "source",
    "release-bottles",
  ]);
  assert.deepEqual(needs(workflow.jobs.tap), [
    "source",
    "release-bottles",
    "verify-installs",
  ]);
  for (const [name, job] of Object.entries(workflow.jobs)) {
    assert.equal(job["continue-on-error"], undefined);
    assert.equal(job.if, undefined);
    for (const step of job.steps) {
      assert.equal(
        step["continue-on-error"],
        undefined,
        `${name} cannot ignore step failures`,
      );
      if (
        name === "verify-installs" &&
        step.uses?.startsWith("actions/upload-artifact@")
      ) {
        assert.equal(
          step.if,
          "always()",
          "failed verification retains diagnostics",
        );
      } else assert.equal(step.if, undefined, `${name} retains success gating`);
    }
  }
});

test("build and verification use matching native Sequoia architectures and prefixes", () => {
  const expected = [
    {
      runner: "macos-15",
      arch: "arm64",
      bottle_tag: "arm64_sequoia",
      prefix: "/opt/homebrew",
    },
    {
      runner: "macos-15-intel",
      arch: "x86_64",
      bottle_tag: "sequoia",
      prefix: "/usr/local",
    },
  ];
  assert.deepEqual(workflow.jobs.bottles.strategy?.matrix?.include, expected);
  assert.deepEqual(
    workflow.jobs["verify-installs"].strategy?.matrix?.include,
    expected,
  );
});

test("tag checkout and artifacts retain the resolved immutable release manifest", () => {
  const source = workflow.jobs.source;
  assert.ok(
    source.steps.some(
      (step) =>
        step.id === "target" && step.run?.startsWith("just release_target"),
    ),
  );
  assert.ok(
    source.steps.some(
      (step) =>
        step.with?.ref === "${{ steps.target.outputs.commit }}" &&
        step.with.path === "release-source",
    ),
  );
  for (const name of ["source", "release-bottles"]) {
    const uploaded = workflow.jobs[name].steps.filter((step) =>
      step.uses?.startsWith("actions/upload-artifact@"),
    );
    assert.ok(
      uploaded.some((step) =>
        String(step.with?.path).includes("dist/release.json"),
      ),
      "release.json travels with each formula artifact",
    );
  }
});

test("tap credentials are restricted to the final job and it checks out the release tools", () => {
  assert.equal(workflow.permissions?.contents, "read");
  for (const [name, job] of Object.entries(workflow.jobs)) {
    for (const step of job.steps)
      if (JSON.stringify(step).includes("HOMEBREW_TAP_TOKEN"))
        assert.equal(name, "tap");
  }
  assert.ok(
    workflow.jobs.tap.steps.some(
      (step) =>
        step.uses?.startsWith("actions/checkout@") &&
        step.with?.repository === undefined,
    ),
    "tap stage has release.ts from the workflow checkout",
  );
});

test("source builds reuse the shared root source recipe and generator", () => {
  assert.equal(
    dryRun("build_knowledge_mcp", ["tagged source", "build output"]),
    "uv build --project 'tagged source' --package knowledge-mcp --sdist --out-dir 'build output'",
  );
  const generated = dryRun("generate_formula", [
    "source archive.tar.gz",
    "formula output.rb",
    "tagged source",
  ]);
  assert.ok(
    generated.includes(
      "node tools/formula/generate-formula.ts --sdist 'source archive.tar.gz' --out 'formula output.rb' --lock 'tagged source/uv.lock' --requirements 'tagged source/runtime/requirements.lock' --pyproject 'tagged source/runtime/pyproject.toml'",
    ),
  );
  assert.equal(
    dryRun("build_knowledge_mcp"),
    "uv build --project '.' --package knowledge-mcp --sdist --out-dir 'dist'",
  );
});
