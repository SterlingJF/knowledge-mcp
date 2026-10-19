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

## Focused checks

Use the recipe for the area you changed while developing; run the full checks before a pull request.

| Area                      | Command                | Checks                                                                                           |
| ------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------ |
| Runtime Python            | `just check_runtime`   | Ruff, strict mypy, Vulture, tests and generated-file drift                                       |
| Schemas                   | `just check_contracts` | Schema lint, conformance samples and generated bundles                                           |
| Docs and repository tools | `just check_root`      | Markdown and relative links, TypeScript, configuration, shell scripts, workflows and module maps |
| Staged files              | `just check_staged`    | Pre-commit checks, including the 5,120 KB limit for added files and Renovate validation          |

The [justfile](justfile) defines each check. Python rules live in [ruff.toml](ruff.toml) and [pyproject.toml](pyproject.toml); repository tooling uses [package.json](package.json) and its referenced configs. The [Markdown config](.markdownlint-cli2.jsonc) includes relative-link checks. [Prettier exclusions](.prettierignore) identify files whose formatting must be preserved.

## Generated and vendored files

Edit YAML schemas in `contracts/extensions/mcp/v1/`, then run `just generate_contract_types` for runtime models and bundles. Run `just generate_contract_snapshots` to refresh `tools.json` and passing conformance samples, then `just generate_mcp_tools_doc` for the tool reference. Write failing conformance samples by hand. See the [contract rules](contracts/README.md).

Keep these boundaries when editing:

- Preserve exact bytes in `runtime/tests/fixtures/`; tests depend on them.
- Refresh bundled universe specs and the six knowledge-bus skills through `just refresh_knowledge_model <tag>`, following the [upgrade steps](runtime/README.md#upgrade-knowledge-bus). Their hashes are recorded in [UPSTREAM.md](runtime/knowledge-bus/UPSTREAM.md).
- Replace vendored anti-slop rules from their source, following [their provenance instructions](tools/oxlint/anti-slop/UPSTREAM.md).
- Generate `runtime/requirements.lock` from `uv.lock` with `just generate_knowledge_mcp_lock`.
- Update copied module maps from their source READMEs as described below.

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
├── extensions/mcp/v1/               # Tool result, error and configuration schemas
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
