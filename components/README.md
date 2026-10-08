# components

Shared UI components and the canonical visual tokens.

## Layout

```text
components/
├── README.md
├── package.json                      check
├── tsconfig.json
├── .oxlintrc.json                    extends ../.oxlintrc.json
├── components.json
├── index.ts                          public surface
├── styles.css                        Tailwind entry; imports the generated CSS and the shell styles
├── shell-patterns.css                layout, chrome, and motion of the shell patterns
├── design/visual-tokens.json         canonical token map (edit this)
├── generated/                        CSS and TypeScript generated from the token map (never edit)
├── lib/                              shared helpers: cn, form factory, metrics, types
├── component-core/                   vendored components, never edited
├── component-elements/               wrappers that extend core components
└── component-patterns/               compositions of elements and core
```

## Visual Tokens

`design/visual-tokens.json` is the only place a token value is written. Its top-level keys match the `DESIGN.md` front matter.

- `colors.primitives`: raw values.
- `colors.roles`: a primitive for `light` and for `dark`, written `{primitive-name}`.
- Numbers take their group's unit (`rem`, `px`, or `ms`); strings are written as given.
- `components.<component>.<property>` becomes `--<component>-<property>`.

The root tool `tools/visual-tokens/` writes:

| Output                             | Contents                                                         |
| ---------------------------------- | ---------------------------------------------------------------- |
| `generated/visual-tokens.auto.css` | CSS custom properties on `:root`, with dark values under `.dark` |
| `generated/visual-tokens.auto.ts`  | `visualTokens` object and the `ColorRole` type                   |
| `DESIGN.md` (root)                 | The YAML front matter; the body is kept                          |

`ThemeProvider` puts `.light` or `.dark` on the root. The generated CSS sets no `color-scheme`.

## Commands

| Command                        | Purpose                                                              |
| ------------------------------ | -------------------------------------------------------------------- |
| `pnpm run check`               | Lint, then type-check                                                |
| `pnpm run lint`                | Lint with oxlint                                                     |
| `just generate_visual_tokens`  | From the repo root: regenerate the outputs and `DESIGN.md`           |
| `just check_visual_tokens`     | From the repo root: fail if the outputs or `DESIGN.md` are stale     |
| `just add_shadcn_atoms dialog` | From the repo root: vendor a shadcn component into `component-core/` |

## Rules

- Change a token in `design/visual-tokens.json`, then regenerate. Never edit `generated/` or the `DESIGN.md` front matter by hand.
- Vendored core is never edited; enrich in elements, compose in patterns.
- Layers import each other by relative path (`../lib/utils`). An app's `@/` alias points at its own `src/`.
- An app imports `components/styles.css` once and each layer by subpath, such as `components/component-patterns/VaultSwitcher`.
