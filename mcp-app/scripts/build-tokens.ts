// Generates src/generated/tokens.auto.css from design/mcp-app/kmtokens.js, the one source for every token.
// The host's own style variables, set on <html> at runtime, override these fallbacks.
// With --check, fails when the generated file is out of date.

import { readFileSync, writeFileSync } from "node:fs";
import { runInNewContext } from "node:vm";

type Tokens = Record<string, Record<string, string>> & {
  color: { light: Record<string, string>; dark: Record<string, string> };
};

const source = new URL("../../design/mcp-app/kmtokens.js", import.meta.url);
const target = new URL("../src/generated/tokens.auto.css", import.meta.url);

type Sandbox = { window: { KMT?: Tokens } };

const sandbox: Sandbox = { window: {} };
runInNewContext(readFileSync(source, "utf8"), sandbox);
const tokens = sandbox.window.KMT;
if (!tokens) throw new Error("kmtokens.js did not set window.KMT");

const block = (
  selector: string,
  values: Record<string, string>,
  extra = "",
): string =>
  `${selector} {\n${Object.entries(values)
    .map(([name, value]) => `  ${name}: ${value};`)
    .join("\n")}${extra}\n}\n`;

const flat = {
  ...tokens.font,
  ...tokens.radius,
  ...tokens.border,
  ...tokens.space,
  ...tokens.motion,
  ...tokens.touch,
  ...tokens.size,
  ...tokens.effect,
};
const css = [
  "/* Generated from design/mcp-app/kmtokens.js by scripts/build-tokens.ts. Edit the tokens, not this file. */\n",
  block(
    ":root",
    { ...tokens.color.light, ...flat },
    "\n  color-scheme: light dark;",
  ),
  block(':root[data-theme="dark"]', tokens.color.dark),
  `@media (prefers-color-scheme: dark) {\n${block(
    ":root:not([data-theme])",
    tokens.color.dark,
  )
    .split("\n")
    .map((line) => (line ? `  ${line}` : line))
    .join("\n")}}\n`,
].join("\n");

if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(target, "utf8");
  } catch {
    // A missing file is out of date too.
  }
  if (current !== css) {
    process.stderr.write(
      "src/generated/tokens.auto.css is out of date. Run pnpm --filter mcp-app tokens.\n",
    );
    process.exit(1);
  }
} else {
  writeFileSync(target, css);
}
