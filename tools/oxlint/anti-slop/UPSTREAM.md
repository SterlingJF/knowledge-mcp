# Upstream

| Files                       | Source                                                                                                                           | License |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `rules/*.ts`, `shared/*.ts` | [dmmulroy/anti-slop `src/` @ `c44ef22`](https://github.com/dmmulroy/anti-slop/tree/c44ef22ca116d0ba62a3ff663a0bd13a3f3fa40b/src) | MIT     |
| `LICENSE`                   | [dmmulroy/anti-slop @ `c44ef22`](https://github.com/dmmulroy/anti-slop/blob/c44ef22ca116d0ba62a3ff663a0bd13a3f3fa40b/LICENSE)    | MIT     |

`index.ts` adapts `src/index.ts` to load the vendored rules with `eslintCompatPlugin`.
Copy updates from the pinned source, then run `just format`.

oxlint and knip skip `rules/` and `shared/`. oxlint lints `index.ts`.
