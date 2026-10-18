import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  cpSync,
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
const scripts = readScripts();
const formatted =
  "export function increment(value: number): number {\n  return value + 1;\n}\n";

function readScripts(): Map<string, string> {
  const manifest: unknown = JSON.parse(
    readFileSync(join(root, "package.json"), "utf8"),
  );
  if (
    typeof manifest !== "object" ||
    manifest === null ||
    !("scripts" in manifest) ||
    typeof manifest.scripts !== "object" ||
    manifest.scripts === null
  ) {
    throw new Error("package.json defines no scripts");
  }
  return new Map(
    Object.entries(manifest.scripts).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  );
}

function script(name: string): string {
  const command = scripts.get(name);
  assert.ok(command, `package.json must define the ${name} script`);
  return command;
}

function fixture(context: TestContext) {
  const dir = mkdtempSync(join(tmpdir(), "tools-quality-"));
  context.after(() => rmSync(dir, { recursive: true, force: true }));
  mkdirSync(join(dir, "tools"));
  // The root lint config loads the vendored anti-slop plugin from tools/oxlint.
  cpSync(join(root, "tools/oxlint"), join(dir, "tools/oxlint"), {
    recursive: true,
  });
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

test("the root lint script checks the TypeScript in tools/ and rejects debugger statements", (context) => {
  assert.ok(
    script("check").includes("pnpm run check:lint"),
    "the root check script must run check:lint",
  );
  const input = fixture(context);
  const clean = input.run(script("check:lint"));
  assert.equal(clean.status, 0, clean.output);
  writeFileSync(
    input.source,
    formatted.replace("  return", "  debugger;\n  return"),
  );
  const rejected = input.run(script("check:lint"));
  assert.notEqual(rejected.status, 0, rejected.output);
  assert.match(rejected.output, /no-debugger/);
});

test("the root lint script loads the anti-slop rules and rejects an unexplained type assertion", (context) => {
  const input = fixture(context);
  writeFileSync(
    input.source,
    'export const port = JSON.parse("1") as number;\n',
  );
  const rejected = input.run(script("check:lint"));
  assert.notEqual(rejected.status, 0, rejected.output);
  assert.match(rejected.output, /require-safety-comment-for-type-assertion/);
});

test("the root format script checks the TypeScript in tools/ and rejects unformatted code", (context) => {
  assert.ok(
    script("check").includes("pnpm run check:format"),
    "the root check script must run check:format",
  );
  const input = fixture(context);
  const command = script("check:format");
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
