import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { test } from "node:test";
import type { TestContext } from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../../", import.meta.url));
const scripts = (
  JSON.parse(readFileSync(join(root, "package.json"), "utf8")) as {
    scripts: Record<string, string>;
  }
).scripts;
const formatted =
  "export function increment(value: number): number {\n  return value + 1;\n}\n";

function fixture(context: TestContext) {
  const dir = mkdtempSync(join(tmpdir(), "tools-quality-"));
  context.after(() => rmSync(dir, { recursive: true, force: true }));
  mkdirSync(join(dir, "tools"));
  symlinkSync(join(root, "node_modules"), join(dir, "node_modules"), "dir");
  const source = join(dir, "tools/fixture.ts");
  writeFileSync(source, formatted);
  writeFileSync(join(dir, "package.json"), '{\n  "type": "module"\n}\n');
  writeFileSync(
    join(dir, "tsconfig.json"),
    JSON.stringify(
      {
        compilerOptions: { strict: true, target: "es2023", module: "nodenext" },
      },
      null,
      2,
    ) + "\n",
  );
  for (const name of [
    ".oxlintrc.json",
    ".prettierrc.json",
    ".prettierignore",
  ]) {
    if (existsSync(join(root, name)))
      copyFileSync(join(root, name), join(dir, name));
  }
  return {
    source,
    run(command: string) {
      const result = spawnSync("bash", ["-c", command], {
        cwd: dir,
        encoding: "utf8",
        env: {
          ...process.env,
          PATH: `${join(root, "node_modules/.bin")}${delimiter}${process.env.PATH ?? ""}`,
        },
      });
      return { status: result.status, output: result.stdout + result.stderr };
    },
  };
}

test("the normal root lint command checks TypeScript tools and rejects debugger statements", (context) => {
  assert.ok(
    scripts["check:lint"],
    "package.json must define the root lint command",
  );
  assert.ok(
    scripts.check.includes("pnpm run check:lint"),
    "the normal root check must run its lint command",
  );
  const input = fixture(context);
  const clean = input.run(scripts["check:lint"]);
  assert.equal(clean.status, 0, clean.output);
  writeFileSync(
    input.source,
    formatted.replace("  return", "  debugger;\n  return"),
  );
  const rejected = input.run(scripts["check:lint"]);
  assert.notEqual(rejected.status, 0, rejected.output);
  assert.match(rejected.output, /no-debugger/);
});

test("the normal root format command checks TypeScript tools and rejects unformatted code", (context) => {
  assert.ok(
    scripts.check.includes("pnpm run check:format"),
    "the normal root check must run its format command",
  );
  const input = fixture(context);
  const command = scripts["check:format"];
  const clean = input.run(command);
  assert.equal(clean.status, 0, clean.output);
  writeFileSync(
    input.source,
    "export function increment( value:number){return value+1}",
  );
  const rejected = input.run(command);
  assert.notEqual(rejected.status, 0, rejected.output);
  assert.match(rejected.output, /fixture\.ts/);
});
