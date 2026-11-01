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

const flat = { ...tokens.font, ...tokens.radius, ...tokens.border };
const host = (name: string): string => `var(${name})`;

// shadcn's names as Tailwind colours, and the host fonts, type sizes, radii and border width its classes read.
const typeSizes = {
  xs: "--font-text-xs",
  sm: "--font-text-sm",
  base: "--font-heading-md",
} satisfies Record<string, string>;
const theme = {
  "--font-sans": host("--font-sans"),
  "--font-mono": host("--font-mono"),
  ...Object.fromEntries(
    Object.keys(tokens.shadcn)
      .filter((name) => name !== "--radius")
      .map((name) => [`--color-${name.slice(2)}`, host(name)]),
  ),
  ...Object.fromEntries(
    Object.entries(typeSizes).flatMap(([size, token]) => [
      [`--text-${size}`, host(`${token}-size`)],
      [`--text-${size}--line-height`, host(`${token}-line-height`)],
    ]),
  ),
  "--radius-sm": host("--border-radius-sm"),
  "--radius-md": host("--border-radius-md"),
  "--radius-lg": host("--border-radius-lg"),
  "--radius-xl": host("--border-radius-xl"),
  "--default-border-width": host("--border-width-regular"),
} satisfies Record<string, string>;

const css = [
  "/* Generated from design/mcp-app/kmtokens.js by scripts/build-tokens.ts. Edit the tokens, not this file. */\n",
  block(
    ":root",
    { ...tokens.color.light, ...flat },
    "\n  color-scheme: light dark;",
  ),
  block(
    ':root[data-theme="dark"],\n[data-theme="dark"]',
    tokens.color.dark,
    "\n  color-scheme: dark;",
  ),
  // A container can force light inside a dark page too (the gallery's light column).
  block('[data-theme="light"]', tokens.color.light, "\n  color-scheme: light;"),
  `@media (prefers-color-scheme: dark) {\n${block(
    ":root:not([data-theme])",
    tokens.color.dark,
  )
    .split("\n")
    .map((line) => (line ? `  ${line}` : line))
    .join("\n")}}\n`,
  "/* shadcn's names, pointed at the host roles; declared on themed containers too, so they re-resolve there. */\n",
  block(":root,\n[data-theme]", tokens.shadcn),
  "/* Tailwind colours, fonts, type sizes, radii and the border width for shadcn's classes. */\n",
  block("@theme inline", theme),
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
} else writeFileSync(target, css);
