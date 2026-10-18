# Contributing

Open an issue to discuss a change before you send a pull request. Report vulnerabilities privately, as [SECURITY.md](./SECURITY.md) describes.

## Development

Install Node (version in `.node-version`), pnpm, uv and [just](https://just.systems/). The pre-push and post-merge hooks also need osv-scanner.

```sh
just install_frozen
uv sync --locked --all-packages
```

`just install_frozen` also installs the Git hooks in `.husky/`.

Run the checks before sending a pull request:

```sh
just check
```

Run `just format` to format files and apply lint fixes. Run `just --list` to list public recipes.

For releases, see [docs/release-check.md](docs/release-check.md).

Renovate updates `uv.lock` but not `runtime/requirements.lock`. When a Renovate PR fails `check_knowledge_mcp_lock`, check out the branch and run `just generate_knowledge_mcp_lock`. Commit and push `runtime/requirements.lock`.

## Lint and format

| Files                                       | Linters                                             | Formatter                             | Config                                                    | Recipe                                                       |
| ------------------------------------------- | --------------------------------------------------- | ------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------ |
| `runtime/knowledge_mcp/` Python             | Ruff, strict mypy, Vulture                          | Ruff                                  | `ruff.toml`, `pyproject.toml`                             | `check_runtime`                                              |
| `runtime/tests/`, `runtime/scripts/` Python | Ruff; Vulture on tests                              | Ruff                                  | `ruff.toml`, `pyproject.toml`                             | `check_runtime`                                              |
| `tools/` TypeScript                         | Type-aware oxlint, anti-slop rules, tsc, Knip       | Prettier                              | `.oxlintrc.json`, `tsconfig.json`, `knip.json`            | `check_root`                                                 |
| Markdown                                    | markdownlint-cli2, relative links                   | Prettier, markdownlint fixes          | `.markdownlint-cli2.jsonc`                                | `check_root`                                                 |
| YAML                                        | Strict yamllint                                     | Prettier                              | `.yamllint.yml`                                           | `check_root`                                                 |
| GitHub workflows                            | actionlint, shellcheck, yamllint                    | Prettier                              | `.yamllint.yml`                                           | `check_root`                                                 |
| JSON Schemas and conformance samples        | Sourcemeta jsonschema, strict Ajv 2020-12           | Prettier                              | `justfile`, `tools/conformance/`                          | `check_contracts`                                            |
| `tools.json` schemas                        | jsonschema, snapshot test                           | `generate_contract_snapshots`         | `justfile`                                                | `check_contracts`, `check_runtime`                           |
| TOML                                        | Tombi                                               | Prettier TOML plugin                  | `.prettierrc.json`                                        | `check_root`                                                 |
| JSON                                        | Prettier; Renovate validator; plugin manifest tests | Prettier                              | `.prettierrc.json`, `.pre-commit-config.yaml`             | `check_root`, `check_staged`, `check_runtime`                |
| `justfile`                                  | just, shellcheck on Bash recipes                    | `just --fmt`                          | `justfile`                                                | `check_root`                                                 |
| `.husky/` hooks                             | shellcheck (sh)                                     | None                                  | `justfile`                                                | `check_root`                                                 |
| Generated models in `models_auto/`          | Strict mypy, drift check                            | Ruff through datamodel-code-generator | `pyproject.toml`                                          | `check_runtime`                                              |
| Schema bundles, tool reference, module maps | Drift checks                                        | `generate_*` recipes                  | `justfile`                                                | `check_contracts`, `check_runtime`, `check_root`             |
| Lockfiles                                   | Locked installs, export comparison, OSV             | None (generated)                      | `.pre-commit-config.yaml`, `justfile`, `osv-scanner.toml` | `check_runtime`, `check_staged`, `scan_dependencies_or_warn` |
| `runtime/tests/fixtures/`                   | Exact-byte tests                                    | None                                  | `.prettierignore`, `.markdownlint-cli2.jsonc`             | `check_runtime`                                              |
| Vendored universe specs and six skills      | SHA-256 comparison                                  | None                                  | `runtime/knowledge-bus/UPSTREAM.md`                       | `check_root`                                                 |
| Vendored rules in `tools/oxlint/anti-slop/` | tsc, rule tests                                     | Prettier                              | `tools/oxlint/anti-slop/UPSTREAM.md`                      | `check_root`                                                 |
| Newly added files                           | Large-file limit: 5,120 KB                          | None                                  | `.pre-commit-config.yaml`                                 | `check_staged`                                               |

## Project map

Edit module maps in [contracts/README.md](contracts/README.md#layout) and [runtime/README.md](runtime/README.md#layout). Run `just generate_readme_maps` to update this guide.

Modules are packages in `pnpm-workspace.yaml`, uv workspace members in `pyproject.toml`, and top-level folders with a README `## Layout` section.

Give each module a README.md, a CI job and a map region under Project map. Add a `check_<name>` recipe to `just check`. Name the job and region after the module folder. Replace hyphens with underscores in the recipe name.

### Root

```text
.
├── runtime/                         # MCP server, kb CLI and skills
├── contracts/                       # Tool results and document-types file schemas
├── tools/                           # Repository maintenance tools
│   ├── modules/                     # Module wiring checks
│   ├── readme-regions/              # Module maps for CONTRIBUTING.md
│   ├── formula/                     # Release, bottle and Homebrew formula scripts
│   └── ...                          # conformance, dependencies, knowledge-model, oxlint
├── docs/                            # MCP tool reference, release runbook, README images
├── .github/workflows/               # CI jobs and release workflow
├── .husky/                          # Git hooks
├── .claude-plugin/, .agents/        # Claude Code and Codex marketplace entries
├── justfile                         # Repo commands
└── ...                              # Top-level docs, LICENSE, configs, lockfiles
```

### contracts

<!-- BEGIN AUTO-GENERATED contracts/README.md#layout -->

```text
contracts/
├── extensions/mcp/v1/               # Tool result, error and document-types schemas
│   ├── *.schema.yaml                # JSON Schemas and shared definitions
│   ├── tools.json                   # tools/list snapshot from the server
│   └── conformance/                 # Pass and fail samples per schema
└── package.json                     # Schema lint tool dependencies
```

<!-- END AUTO-GENERATED contracts/README.md#layout -->

### runtime

<!-- BEGIN AUTO-GENERATED runtime/README.md#layout -->

```text
runtime/
├── .claude-plugin/, .codex-plugin/  # Claude Code and Codex plugin manifests
├── codex-mcp.json                   # Codex MCP server entry
├── knowledge_mcp/
│   ├── cli.py                       # kb entry point
│   ├── main.py                      # MCP server entry point
│   ├── start.py                     # Plugin entry point with cached environment
│   ├── tools/                       # MCP tool modules
│   ├── models_auto/, schemas_auto/  # Generated models and schema bundles
│   └── ...                          # Setup, settings, validation, imports and file history
├── knowledge-bus/                   # Vendored spec files
├── skills/                          # Six knowledge-bus skills and three knowledge-mcp skills
├── scripts/                         # docs/mcp-tools.md region generator
└── tests/                           # Unit and end-to-end tests
```

<!-- END AUTO-GENERATED runtime/README.md#layout -->

## Related projects

- [knowledge-bus](https://github.com/SterlingJF/knowledge-bus): source of the vendored universe specs, the six vendored skills and the kbp validator.
