# Worker brief

You build one card from [todo.md](todo.md) in your own git worktree, on your own branch. You know only this brief and your card. Read [plan.md](plan.md) first.

## Sources of truth

- **Frames:** [frames.md](frames.md) lists every frame on the storyboard canvas `MVdPWv1RzA` with a public PNG for light and dark (`curl -o k01.png <url>`, then read the image). The canvas API needs a Doop session, so don't use it. Read your parts' sheets and the frames listed under "Used in" on each sheet.
- **Generator code:** `design/mcp-app/kmgen.js` and `ds.js` contain the exact CSS and markup each frame was drawn with. Port their structure; don't guess.
- **Tokens:** only `mcp-app/src/generated/tokens.auto.css` (host style variables, `--km-space-*`, `--km-icon`, `--km-check`, `--km-dot`, `--km-label-col`, `--km-row`, `--km-target`) and `src/styles.css`, which also holds the shared `km-pulse` and `km-shimmer` keyframes. Never write a raw colour, size, radius, space or duration, and never define keyframes in a component.
- **Copy:** only `mcp-app/src/copy/en.ts`. Missing a string? Add it in a block at the end of the file headed `// <your card>`, following F07, and list each one in your report.
- **Claude's rules:** F00 on the Foundations page. Inline cards: at most 5 data points, 2 actions, no inner scrolling, 44pt touch targets, no spinners, transparent background.

## The CE Pattern

`/Users/sterlingfreeman/Desktop/side_projects/cardtrail-evolution-1/tools/ce-pattern/README_COMPONENT_SYSTEM.md` (read only). It wins over the shadcn skill where they conflict.

- `src/component-core/` is shadcn vendor code. Never edit it. Wrap it in an element.
- An element imports at most one component source and exports at least as many things as it imports.
- A pattern imports two or more and exports fewer. Dependencies only flow down.

## Skills

Use these and say which you used in your report: test-driven-development, shadcn, web-design-guidelines, browser-testing-with-devtools, design-taste-frontend, code-review-and-quality.

## Loop

1. Run `pnpm install` in your worktree (and `uv sync` for runtime work).
2. Look at every frame PNG your card names, light and dark, before writing code; the generator markup alone misses layout. Then write a failing test first wherever behaviour isn't trivial (states, counts, refusals, events). Use Vitest and Testing Library; test what the user sees.
3. Build the parts your card names, nothing else. Add a `<name>.gallery.tsx` beside each element or pattern. It default-exports `{ id, name, stories }`, with one story per state on its sheet, and `pnpm --filter mcp-app dev` shows it at `/gallery.html` in light and dark.
4. Format from the repo root (`pnpm exec prettier --write mcp-app`), never from inside `mcp-app/`, or generated files get reformatted. Run `pnpm --filter mcp-app run check` (app) or `just check_runtime` (runtime) until it passes.
5. Commit on your branch with one terse line, no body, no attribution (`feat: add badge and button elements`). Never push.
6. Report: the commit, files changed, tests added, skills used, and anything you stopped on.

## Stop and report instead of guessing

- You need to edit a file your card doesn't own, or a shared file: `design/mcp-app/*`, `src/generated/*`, `src/copy/*`, `package.json`, `pnpm-lock.yaml`, `contracts/*`, `justfile`, CI, `CONTRIBUTING.md`.
- A frame can't be built as drawn, or two sources disagree.
- You'd need a new dependency.
