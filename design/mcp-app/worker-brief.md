# Worker brief

You build one card from [todo.md](todo.md) in your own git worktree, on your own branch. You know only this brief and your card. Read [plan.md](plan.md) first.

## Sources of truth

- **Frames:** the storyboard canvas `MVdPWv1RzA` on the Doop server at `http://localhost:4300`. `GET /api/canvases/MVdPWv1RzA` lists frames with their HTML. Pages: 00 Foundations, 00 Components (K00–K13), 00 Patterns (P01–P07), then the flows. Read your parts' sheets and the frames listed under "Used in".
- **Generator code:** `design/mcp-app/kmgen.js` and `ds.js` contain the exact CSS and markup each frame was drawn with. Port their structure; don't guess.
- **Tokens:** only `mcp-app/src/generated/tokens.auto.css` (host style variables) and `src/styles.css`. Never write a raw colour, size, radius, space or duration.
- **Copy:** only `mcp-app/src/copy/en.ts`. Missing a string? Stop and report it; the coordinator adds it.
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
2. Write a failing test first wherever behaviour isn't trivial (states, counts, refusals, events). Use Vitest and Testing Library; test what the user sees.
3. Build the parts your card names, nothing else. Add a `<name>.gallery.tsx` beside each element or pattern. It default-exports `{ id, name, stories }`, with one story per state on its sheet, and `pnpm --filter mcp-app dev` shows it at `/gallery.html` in light and dark.
4. Run `pnpm --filter mcp-app run check` (app) or `just check_runtime` (runtime) until it passes.
5. Commit on your branch with one terse line, no body, no attribution (`feat: add badge and button elements`). Never push.
6. Report: the commit, files changed, tests added, skills used, and anything you stopped on.

## Stop and report instead of guessing

- You need to edit a file your card doesn't own, or a shared file: `design/mcp-app/*`, `src/generated/*`, `src/copy/*`, `package.json`, `pnpm-lock.yaml`, `contracts/*`, `justfile`, CI, `CONTRIBUTING.md`.
- A frame can't be built as drawn, or two sources disagree.
- You'd need a new dependency.
