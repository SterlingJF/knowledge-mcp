# Upstream

Provenance for the vendored CE pattern tooling. Updates follow the kit's `references/update.md`
as a three-way merge; this directory is never replaced wholesale.

## Source

- Repository: SterlingJF/ce-pattern-kit
- Ref: b4e59c2
- Commit: b4e59c28603a950a2e22f5ed4c06873f76d09392
- Skill: install-ce-pattern

## Installed paths

- Tooling: `tools/ce-pattern/`
- Library: `mcp-app/` (`@`, preset react-shadcn, style base-vega)
- Consumers: none

## Deviations

- First installed from a36665c with `install.mjs --roots mcp-app`; the checker, its tests and
  fixtures, `justfile.ce`, `add-shadcn-items.mjs` and `check-shadcn-core.mjs` were replaced from
  b4e59c2 by hand. `add-styling.mjs` was not run: `design/mcp-app/kmtokens.js` stays the token
  source, so there is no `tokens.json`, `generate-tokens.mjs` or Rule 8 lint yet.
- `ce-pattern.json` records the library by hand and sets `supportSuffixes` for the
  `.gallery.tsx` and `.harness.tsx` files that sit beside their components.
- The justfile recipes `check_component_layers` and `check_shadcn_core` are written by hand and
  run from `check_mcp_app`; `justfile.ce` is kept for reference only.
- The root `.oxlintrc.json`, `tsconfig.json`, `knip.json` and `test` glob exclude
  `tools/ce-pattern/`; `check:component-layers` runs its tests with `tsx`.

## Verification

```bash
pnpm run check:component-layers
```
