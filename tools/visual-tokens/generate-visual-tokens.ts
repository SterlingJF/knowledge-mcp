#!/usr/bin/env node

// Generates CSS, TypeScript and optional DESIGN.md front matter from a visual token map.
// A number takes its group's unit; a string is written as given. Each component's
// properties become `--<component>-<property>` custom properties.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

import { format } from "prettier";
import { stringify } from "yaml";

type Scheme = { light: string; dark: string };
type Scale = Record<string, string | number>;

type Tokens = {
  version: string;
  name: string;
  description: string;
  colors: { primitives: Record<string, string>; roles: Record<string, Scheme> };
  typography: { families: Scale; sizes: Scale; leading: Scale };
  rounded: Scale;
  spacing: Scale;
  components: Record<string, Scale>;
  motion: { durations: Scale; easings: Scale };
  elevation: Scale;
  layers: Scale;
};

const groups = [
  "version",
  "name",
  "description",
  "colors",
  "typography",
  "rounded",
  "spacing",
  "components",
  "motion",
  "elevation",
  "layers",
] as const;

const usage =
  "Usage: generate-visual-tokens --tokens <visual-tokens.json> --out <dir> [--design <DESIGN.md>] [--dark media|class] [--check]";
const generator = "tools/visual-tokens/generate-visual-tokens.ts";

const options = readArgs();
const tokensPath = resolve(options.tokens);
const outDir = resolve(options.out);
const tokens = readTokens(tokensPath);
const primitives = tokens.colors.primitives;
const roles = Object.fromEntries(
  Object.entries(tokens.colors.roles).map(([role, scheme]) => [
    role,
    {
      light: primitives[referenceName(role, scheme.light)],
      dark: primitives[referenceName(role, scheme.dark)],
    },
  ]),
);
const banner = `Generated from ${toPosix(relative(process.cwd(), tokensPath))} by ${generator}. Do not edit.`;

const outputs: [string, string][] = [
  [join(outDir, "visual-tokens.auto.css"), await renderCss()],
  [join(outDir, "visual-tokens.auto.ts"), await renderTs()],
];
if (options.design) {
  const designPath = resolve(options.design);
  outputs.push([designPath, await renderDesign(designPath)]);
}

let stale = false;
for (const [path, generated] of outputs) {
  if (readOptional(path) === generated) continue;
  const label = toPosix(relative(process.cwd(), path));
  if (options.check) {
    console.error(`stale: ${label}`);
    stale = true;
  } else {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, generated);
    console.log(`wrote: ${label}`);
  }
}
if (stale) process.exitCode = 1;

function readArgs(): {
  tokens: string;
  out: string;
  design?: string;
  dark: "media" | "class";
  check: boolean;
} {
  try {
    const { values } = parseArgs({
      options: {
        tokens: { type: "string" },
        out: { type: "string" },
        design: { type: "string" },
        dark: { type: "string", default: "media" },
        check: { type: "boolean", default: false },
      },
      strict: true,
    });
    if (!values.tokens || !values.out) fail(usage);
    if (values.dark !== "media" && values.dark !== "class") fail(usage);
    return {
      tokens: values.tokens,
      out: values.out,
      design: values.design,
      dark: values.dark,
      check: values.check,
    };
  } catch {
    return fail(usage);
  }
}

function readTokens(path: string): Tokens {
  const parsed = JSON.parse(readFileSync(path, "utf8")) as Record<
    string,
    unknown
  >;
  for (const group of Object.keys(parsed)) {
    if (!(groups as readonly string[]).includes(group)) {
      fail(`Unknown token group: ${group}`);
    }
  }
  for (const group of groups) {
    if (!(group in parsed)) fail(`Missing token group: ${group}`);
  }
  for (const [component, properties] of Object.entries(
    parsed.components as Record<string, unknown>,
  )) {
    if (!isScale(properties)) {
      fail(`Component ${component} must map property names to values`);
    }
  }
  return parsed as Tokens;
}

function declarations(prefix: string, scale: Scale, unit = ""): string[] {
  return Object.entries(scale).map(
    ([name, value]) =>
      `--${prefix}${name}: ${typeof value === "number" ? `${value}${unit}` : value};`,
  );
}

function isScale(value: unknown): value is Scale {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.values(value).every(
      (entry) => typeof entry === "string" || typeof entry === "number",
    )
  );
}

async function renderCss(): Promise<string> {
  const root = [
    ...declarations("palette-", primitives),
    ...Object.entries(tokens.colors.roles).map(
      ([role, scheme]) =>
        `--${role}: var(--palette-${referenceName(role, scheme.light)});`,
    ),
    ...declarations("font-family-", tokens.typography.families),
    ...declarations("type-", tokens.typography.sizes, "rem"),
    ...declarations("leading-", tokens.typography.leading),
    ...declarations("", tokens.rounded, "px"),
    ...declarations("space-", tokens.spacing, "rem"),
    ...declarations("duration-", tokens.motion.durations, "ms"),
    ...declarations("ease-", tokens.motion.easings),
    ...declarations("shadow-", tokens.elevation),
    ...declarations("layer-", tokens.layers),
    ...Object.entries(tokens.components).flatMap(([component, properties]) =>
      declarations(`${component}-`, properties),
    ),
  ];
  const dark = Object.entries(tokens.colors.roles).map(
    ([role, scheme]) =>
      `--${role}: var(--palette-${referenceName(role, scheme.dark)});`,
  );
  // media: dark roles follow the system unless the root has .light, and .dark forces them.
  // class: only .dark switches roles, and the page keeps the browser's default color-scheme.
  const blocks =
    options.dark === "media"
      ? [
          `:root {\ncolor-scheme: light dark;\n${root.join("\n")}\n}`,
          `@media (prefers-color-scheme: dark) {\n:root:not(.light) {\n${dark.join("\n")}\n}\n}`,
        ]
      : [`:root {\n${root.join("\n")}\n}`];
  blocks.push(`.dark {\n${dark.join("\n")}\n}`);
  return format(`/* ${banner} */\n\n${blocks.join("\n\n")}\n`, {
    parser: "css",
  });
}

async function renderTs(): Promise<string> {
  return format(
    `// ${banner}

export const visualTokens = ${JSON.stringify({ ...tokens, colors: { primitives, roles } })} as const;

export type ColorRole = keyof typeof visualTokens.colors.roles;
`,
    { parser: "typescript" },
  );
}

async function renderDesign(path: string): Promise<string> {
  const existing = readOptional(path) ?? "";
  const body = existing.startsWith("---\n")
    ? existing.slice(existing.indexOf("\n---\n", 4) + 5)
    : existing;
  const frontMatter = Object.fromEntries(
    groups.map((group) => [
      group,
      group === "colors" ? { primitives, roles } : tokens[group],
    ]),
  );
  return format(`---\n${stringify(frontMatter)}---\n\n${body.trimStart()}`, {
    parser: "markdown",
  });
}

function referenceName(role: string, reference: string): string {
  const match = /^\{([a-z0-9-]+)\}$/.exec(reference);
  if (!match) fail(`Role ${role} must reference a primitive: ${reference}`);
  if (!(match[1] in primitives)) {
    fail(`Role ${role} references unknown primitive: ${match[1]}`);
  }
  return match[1];
}

function readOptional(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

function toPosix(path: string): string {
  return path.split("\\").join("/");
}

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}
