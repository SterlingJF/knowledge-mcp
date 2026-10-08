import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const script = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "generate-visual-tokens.ts",
);

const tokens = {
  version: "alpha",
  name: "demo",
  description: "Demo tokens.",
  colors: {
    primitives: { "ink-900": "#111111", "paper-50": "#fafafa" },
    roles: {
      background: { light: "{paper-50}", dark: "{ink-900}" },
      foreground: { light: "{ink-900}", dark: "{paper-50}" },
    },
  },
  typography: {
    families: { sans: "system-ui, sans-serif" },
    sizes: { base: 1 },
    leading: { normal: 1.5 },
  },
  rounded: { radius: 6 },
  spacing: { gutter: 1 },
  components: {},
  motion: {
    durations: { fast: 120 },
    easings: { standard: "ease" },
  },
  elevation: { hairline: "0 0 0 1px var(--foreground)" },
  layers: { overlay: 50 },
};

function workspace(overrides: Record<string, unknown> = {}): string {
  const dir = mkdtempSync(join(tmpdir(), "visual-tokens-"));
  mkdirSync(join(dir, "design"));
  writeFileSync(
    join(dir, "design/visual-tokens.json"),
    JSON.stringify({ ...tokens, ...overrides }),
  );
  writeFileSync(
    join(dir, "DESIGN.md"),
    "---\nname: old\n---\n\n## Overview\n\nKept.\n",
  );
  return dir;
}

function run(dir: string, ...extra: string[]) {
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--tokens",
      "design/visual-tokens.json",
      "--out",
      "generated",
      ...extra,
    ],
    { cwd: dir, encoding: "utf8" },
  );
  return { status: result.status, output: result.stdout + result.stderr };
}

const read = (dir: string, path: string): string =>
  readFileSync(join(dir, path), "utf8");

test("writes CSS custom properties with light and dark roles", () => {
  const dir = workspace();
  assert.equal(run(dir).status, 0);
  const css = read(dir, "generated/visual-tokens.auto.css");
  assert.match(css, /--palette-ink-900: #111111;/);
  assert.match(css, /--background: var\(--palette-paper-50\);/);
  assert.match(
    css,
    /prefers-color-scheme: dark[\s\S]*--background: var\(--palette-ink-900\);/,
  );
  assert.match(css, /--radius: 6px;/);
});

test("writes a typed TypeScript token object", () => {
  const dir = workspace();
  run(dir);
  const ts = read(dir, "generated/visual-tokens.auto.ts");
  assert.match(ts, /export const visualTokens = \{/);
  assert.match(ts, /background: \{ light: "#fafafa", dark: "#111111" \}/);
  assert.match(ts, /export type ColorRole = keyof typeof visualTokens/);
});

test("marks generated files with their source and generator", () => {
  const dir = workspace();
  run(dir);
  assert.match(
    read(dir, "generated/visual-tokens.auto.css"),
    /Generated from design\/visual-tokens\.json by tools\/visual-tokens\/generate-visual-tokens\.ts\. Do not edit\./,
  );
});

test("replaces DESIGN.md front matter and keeps the body", () => {
  const dir = workspace();
  assert.equal(run(dir, "--design", "DESIGN.md").status, 0);
  const design = read(dir, "DESIGN.md");
  assert.match(design, /^---\nversion: alpha\nname: demo\n/);
  assert.match(design, /\n---\n\n## Overview\n\nKept\.\n$/);
  assert.doesNotMatch(design, /name: old/);
});

test("check passes when outputs are current", () => {
  const dir = workspace();
  run(dir, "--design", "DESIGN.md");
  assert.equal(run(dir, "--design", "DESIGN.md", "--check").status, 0);
});

test("check fails on drift and writes nothing", () => {
  const dir = workspace();
  const { status, output } = run(dir, "--check");
  assert.equal(status, 1);
  assert.match(output, /stale: generated\/visual-tokens\.auto\.css/);
  assert.throws(() => read(dir, "generated/visual-tokens.auto.css"));
});

test("fails on an unknown token group", () => {
  const dir = workspace({ shadows: {} });
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /Unknown token group: shadows/);
});

test("fails when a role names a missing primitive", () => {
  const dir = workspace({
    colors: {
      primitives: {},
      roles: { background: { light: "{nope}", dark: "{nope}" } },
    },
  });
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /unknown primitive: nope/);
});

test("fails without the required arguments", () => {
  const result = spawnSync(process.execPath, [script], { encoding: "utf8" });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Usage:/);
});

test("writes a string value as given and a number with its group's unit", () => {
  const dir = workspace({
    spacing: { gutter: 1, tight: "4px" },
    typography: {
      families: { sans: "system-ui, sans-serif" },
      sizes: { base: 1, meta: "12px" },
      leading: { normal: 1.5, meta: "16px" },
    },
  });
  assert.equal(run(dir).status, 0);
  const css = read(dir, "generated/visual-tokens.auto.css");
  assert.match(css, /--space-gutter: 1rem;/);
  assert.match(css, /--space-tight: 4px;/);
  assert.match(css, /--type-meta: 12px;/);
  assert.match(css, /--leading-meta: 16px;/);
});

test("writes each component property as a custom property", () => {
  const dir = workspace({
    components: { "app-bar": { height: "40px", "icon-scale": 16 } },
  });
  assert.equal(run(dir).status, 0);
  const css = read(dir, "generated/visual-tokens.auto.css");
  assert.match(css, /--app-bar-height: 40px;/);
  assert.match(css, /--app-bar-icon-scale: 16;/);
  assert.match(
    read(dir, "generated/visual-tokens.auto.ts"),
    /components: \{ "app-bar": \{ height: "40px", "icon-scale": 16 \} \}/,
  );
});

test("fails when a component is not a map of values", () => {
  const dir = workspace({ components: { "app-bar": "40px" } });
  const { status, output } = run(dir);
  assert.equal(status, 1);
  assert.match(output, /Component app-bar must map property names to values/);
});

test("class dark mode switches roles under .dark only and sets no color-scheme", () => {
  const dir = workspace();
  assert.equal(run(dir, "--dark", "class").status, 0);
  const css = read(dir, "generated/visual-tokens.auto.css");
  assert.doesNotMatch(css, /prefers-color-scheme/);
  assert.doesNotMatch(css, /color-scheme:/);
  assert.match(css, /\.dark \{\n {2}--background: var\(--palette-ink-900\);/);
});

test("media dark mode is the default", () => {
  const dir = workspace();
  run(dir);
  const fallback = read(dir, "generated/visual-tokens.auto.css");
  assert.equal(run(dir, "--dark", "media", "--check").status, 0);
  assert.match(fallback, /color-scheme: light dark;/);
  assert.match(fallback, /:root:not\(\.light\)/);
});

test("fails on an unknown dark mode", () => {
  const { status, output } = run(workspace(), "--dark", "auto");
  assert.equal(status, 1);
  assert.match(output, /Usage:/);
});
