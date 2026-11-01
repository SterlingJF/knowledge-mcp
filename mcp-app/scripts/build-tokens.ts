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
  ...tokens.gap,
  ...tokens.pad,
  ...tokens.motion,
  ...tokens.touch,
  ...tokens.size,
  ...tokens.effect,
};
// shadcn's names, pointed at the host roles, so core components follow Claude's theme.
// Also declared on themed containers, so they re-resolve inside a dark preview.
const shadcn = {
  "--background": "transparent",
  "--foreground": "var(--color-text-primary)",
  "--primary": "var(--color-background-inverse)",
  "--primary-foreground": "var(--color-text-inverse)",
  // Crossover: shadcn's secondary surface is the host's background-primary, so bg-secondary is that role.
  "--secondary": "var(--color-background-primary)",
  "--secondary-foreground": "var(--color-text-primary)",
  "--muted": "var(--color-background-secondary)",
  "--muted-foreground": "var(--color-text-tertiary)",
  "--accent": "var(--color-background-secondary)",
  "--accent-foreground": "var(--color-text-primary)",
  "--destructive": "var(--color-text-danger)",
  "--border": "var(--color-border-tertiary)",
  "--input": "var(--color-border-secondary)",
  "--ring": "var(--color-ring-primary)",
  "--radius": "var(--border-radius-md)",
} satisfies Record<string, string>;

// The shadcn names as Tailwind colours, and the host fonts and radii shadcn's classes read.
const shadcnTheme = {
  "--font-sans": "var(--font-sans)",
  "--font-mono": "var(--font-mono)",
  ...Object.fromEntries(
    Object.keys(shadcn)
      .filter((name) => name !== "--radius")
      .map((name) => [`--color-${name.slice(2)}`, `var(${name})`]),
  ),
  "--radius-sm": "var(--border-radius-sm)",
  "--radius-md": "var(--border-radius-md)",
  "--radius-lg": "var(--border-radius-lg)",
  "--radius-xl": "var(--border-radius-xl)",
} satisfies Record<string, string>;

const host = (name: string): string => `var(${name})`;
const renamed = (
  values: Record<string, string>,
  rename: (name: string) => string | null,
): Record<string, string> =>
  Object.fromEntries(
    Object.keys(values).flatMap((name) => {
      const to = rename(name);
      return to ? [[to, host(name)]] : [];
    }),
  );
const statuses = ["info", "success", "warning", "danger"];

// The app's own roles, by utility, so bg-success and text-success name different host variables.
// Roles shadcn already names (foreground, muted, border, input, ring, destructive) use shadcn's class.
const colourTheme = {
  "--background-color-inverse": host("--color-background-inverse"),
  "--background-color-tertiary": host("--color-background-tertiary"),
  ...Object.fromEntries(
    statuses.map((s) => [
      `--background-color-${s}`,
      host(`--color-background-${s}`),
    ]),
  ),
  "--text-color-inverse": host("--color-text-inverse"),
  "--text-color-secondary": host("--color-text-secondary"),
  ...Object.fromEntries(
    statuses
      .filter((s) => s !== "danger")
      .map((s) => [`--text-color-${s}`, host(`--color-text-${s}`)]),
  ),
  "--border-color-inverse": host("--color-background-inverse"),
} satisfies Record<string, string>;

// Type, spacing, radius, borders, motion and effects as Tailwind theme namespaces: a token becomes a class.
const typeSizes = {
  xs: "--font-text-xs",
  sm: "--font-text-sm",
  base: "--font-heading-md",
} satisfies Record<string, string>;
const scaleTheme = {
  "--font-weight-normal": host("--font-weight-normal"),
  "--font-weight-semibold": host("--font-weight-semibold"),
  ...Object.fromEntries(
    Object.entries(typeSizes).flatMap(([size, token]) => [
      [`--text-${size}`, host(`${token}-size`)],
      [`--text-${size}--line-height`, host(`${token}-line-height`)],
      [`--leading-${size}`, host(`${token}-line-height`)],
    ]),
  ),
  ...renamed(tokens.space, (name) =>
    name.replace("--km-space-", "--spacing-km-"),
  ),
  ...renamed({ ...tokens.gap, ...tokens.pad, ...tokens.touch }, (name) =>
    name.replace("--km-", "--spacing-km-"),
  ),
  ...renamed(tokens.size, (name) =>
    ["--km-check-border", "--km-label-col"].includes(name)
      ? null
      : name.replace("--km-", "--spacing-km-"),
  ),
  ...renamed(tokens.radius, (name) =>
    name.replace("--border-radius-", "--radius-"),
  ),
  "--radius-km-1": host("--km-space-1"),
  "--border-width-hairline": host("--border-width-regular"),
  "--border-width-km-check": host("--km-check-border"),
  ...Object.fromEntries(
    Object.keys(tokens.motion).map((name) => [
      `--animate-${name.slice(2)}`,
      `${name.slice(2)} ${host(name)}`,
    ]),
  ),
  "--shadow-km-focus-ring": host("--km-focus-ring"),
  "--tracking-km-eyebrow": host("--km-eyebrow-tracking"),
  "--opacity-km-hover": host("--km-opacity-hover"),
  "--opacity-km-dim": host("--km-opacity-dim"),
  "--opacity-km-disabled": host("--km-opacity-disabled"),
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
  // Effects reference colours, so they re-resolve inside every themed container.
  block("[data-theme]", tokens.effect),
  `@media (prefers-color-scheme: dark) {\n${block(
    ":root:not([data-theme])",
    tokens.color.dark,
  )
    .split("\n")
    .map((line) => (line ? `  ${line}` : line))
    .join("\n")}}\n`,
  "/* shadcn's names, pointed at the host roles. */\n",
  block(":root,\n[data-theme]", shadcn),
  "/* Tailwind colours, fonts and radii for shadcn's classes. */\n",
  block("@theme inline", shadcnTheme),
  "/* The app's own colour roles, by utility: bg-inverse, text-inverse, bg-tertiary, text-secondary, bg-success, text-success. */\n",
  block("@theme inline reference", colourTheme),
  "/* Type, spacing, radius, borders, motion and effects: text-sm, p-km-5, gap-km-gap-group, rounded-sm, border-hairline, animate-km-pulse, shadow-km-focus-ring. */\n",
  block("@theme inline reference", scaleTheme),
].join("\n");

// The same names for tailwind-merge, so cn() knows p-km-5 is padding and border-hairline a width, not a colour.
const names = (
  theme: Record<string, string>,
  prefix: string,
  skip = "",
): Array<string> =>
  Object.keys(theme)
    .filter((name) => name.startsWith(prefix) && !(skip && name.includes(skip)))
    .map((name) => name.slice(prefix.length));
const merge = {
  spacing: names(scaleTheme, "--spacing-"),
  text: names(scaleTheme, "--text-", "--line-height"),
  leading: names(scaleTheme, "--leading-"),
  radius: names(scaleTheme, "--radius-"),
  shadow: names(scaleTheme, "--shadow-"),
  tracking: names(scaleTheme, "--tracking-"),
  animate: names(scaleTheme, "--animate-"),
  opacity: names(scaleTheme, "--opacity-"),
  borderWidth: names(scaleTheme, "--border-width-"),
  color: [
    ...new Set([
      ...names(colourTheme, "--background-color-"),
      ...names(colourTheme, "--text-color-"),
      ...names(colourTheme, "--border-color-"),
    ]),
  ],
};
const ts = `// Generated from design/mcp-app/kmtokens.js by scripts/build-tokens.ts. Edit the tokens, not this file.
// The token class names, for tailwind-merge's theme in lib/utils.ts.
export const tokenClasses = ${JSON.stringify(merge, null, 2)} as const;
`;

const outputs: Array<[URL, string]> = [
  [target, css],
  [new URL("../src/generated/token-classes.auto.ts", import.meta.url), ts],
];
if (process.argv.includes("--check")) {
  for (const [file, content] of outputs) {
    let current = "";
    try {
      current = readFileSync(file, "utf8");
    } catch {
      // A missing file is out of date too.
    }
    if (current !== content) {
      process.stderr.write(
        `${file.pathname.split("/mcp-app/")[1]} is out of date. Run pnpm --filter mcp-app tokens.\n`,
      );
      process.exit(1);
    }
  }
} else {
  for (const [file, content] of outputs) writeFileSync(file, content);
}
