# Contributing

Issues welcome; PRs by discussion first. Report vulnerabilities privately: see [SECURITY.md](./SECURITY.md).

## Development

Needs Node (`.node-version`), pnpm, uv and [just](https://just.systems/). The pre-push and post-merge hooks also need osv-scanner.

```sh
just install_frozen
uv sync --locked --all-packages
```

`just install_frozen` also installs the Git hooks. Large-file check: `uv run pre-commit run --all-files`.

From the repo root:

| Command                              | Purpose                                                                                                           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `just check`                         | Run every check CI runs; changes nothing                                                                          |
| `just generate_mcp_tools_doc`        | Write the intro and the tool tables in `docs/mcp-tools.md`                                                        |
| `just refresh_knowledge_model <tag>` | Copy knowledge-bus's universe specs and skills at `<tag>`, the tag of the pinned release archive, into `runtime/` |
| `just generate_knowledge_mcp_lock`   | Write `runtime/requirements.lock` from `uv.lock`                                                                  |
| `just build_knowledge_mcp`           | Build `dist/knowledge_mcp-<version>.tar.gz`, the source archive the formula installs                              |
| `just generate_formula <archive>`    | Write `dist/knowledge-mcp.rb`, the Homebrew formula, from `uv.lock`                                               |
| `just generate_readme_maps`          | Fill the module maps in this guide                                                                                |
| `just scan_dependencies`             | Scan the lockfiles with OSV                                                                                       |

Each module's README lists its own commands.

A stable tag `vX.Y.Z` matching the tagged `runtime/pyproject.toml` runs the release workflow through the root `release_*` recipes. It builds native ARM64 and Intel macOS bottles and checks bottle and source installs before updating [SterlingJF/homebrew-tap](https://github.com/SterlingJF/homebrew-tap). The `HOMEBREW_TAP_TOKEN` secret needs read and write access to the tap's contents alone. Follow [the release check](docs/release-check.md) for runners, bottle backfills for existing releases, retries, install timing and app checks.

Renovate updates `uv.lock` but not `runtime/requirements.lock`, so `check_knowledge_mcp_lock` fails on its Python update PRs, the weekly lock maintenance PR included. Check out the PR branch, run `just generate_knowledge_mcp_lock`, and push the result.

## Project Map

> The module maps below are generated from the Layout sections in [contracts/README.md](contracts/README.md#layout) and [runtime/README.md](runtime/README.md#layout). Edit those source sections, then run `just generate_readme_maps`. Edit the root map and explanatory text directly in `CONTRIBUTING.md`.

A module is a workspace package, or a root folder whose README has a `## Layout` section. Its folder name is also its:

- CI job
- `check_<name>` recipe, run by `just check` (hyphens become underscores)
- generated Layout region below

Package names are declared separately; `runtime/` distributes the `knowledge-mcp` package.

To add, rename, or remove a module, change these names and the files in its "Referenced from root" line, then run `just generate_readme_maps`. `just check` fails when the names disagree.

### Root

```text
.
├── README.md
├── CONTRIBUTING.md             development and repository layout
├── CHANGELOG.md                 what changed in each release
├── SECURITY.md
├── LICENSE
├── justfile                     commands run from the repo root
├── package.json                 root Node tooling
├── pnpm-workspace.yaml          Node modules
├── pnpm-lock.yaml
├── .node-version                Node version for local and CI
├── tsconfig.json                type-checks tools/
├── pyproject.toml               Python workspace root
├── uv.lock
├── .python-version
├── .husky/                      Git hooks
├── .pre-commit-config.yaml      large-file guard
├── .github/workflows/ci.yml     one job per module
├── .github/workflows/release.yml  version tag or manual backfill: source archive, macOS bottles, validated formula to the tap
├── .gitignore
├── .prettierrc.json
├── .prettierignore
├── .markdownlint-cli2.jsonc
├── ruff.toml
├── .yamllint.yml
├── renovate.json
├── osv-scanner.toml
├── .evidence/README.md          local evidence archive; only the README is tracked
├── .claude-plugin/marketplace.json  Claude Code marketplace: one entry, ./runtime
├── .agents/plugins/marketplace.json Codex marketplace: one entry, ./runtime
├── docs/                        product docs: MCP tools, the release check
├── skills/
├── tools/                       repo maintenance, one folder per tool
│   ├── modules/                 checks every module is wired the same way
│   ├── readme-regions/          fills the module maps below
│   ├── conformance/             checks contract samples
│   ├── dependencies/            scans the lockfiles for vulnerabilities
│   ├── placeholders/            checks no project-template placeholder is left
│   ├── knowledge-model/         copies knowledge-bus's universe specs and skills into runtime/
│   └── formula/                 writes the Homebrew formula from uv.lock
├── contracts/                   module
└── runtime/                     module
```

### contracts

<!-- BEGIN AUTO-GENERATED contracts/README.md#layout -->

```text
contracts/
├── README.md
├── package.json                              lint
├── redocly.yaml                              lint policy for every OpenAPI file
├── project/                                  this project's own modules talk to each other
│   └── v1/
│       ├── <name>.rest.openapi.yaml          request / response
│       ├── <name>.realtime-sse.openapi.yaml  event stream
│       ├── <name>.schema.yaml                data shape
│       └── conformance/
│           ├── pass/<name>.<case>.yaml       must validate against <name>.schema.yaml
│           └── fail/<name>.<case>.yaml       must not validate
├── plugins/<name>/                           outside code plugs into this project
│   └── v1/                                   same shape as project/v1
└── extensions/                               this project reaches into another project
    └── <target>/
        ├── upstream/                         the target's spec, vendored read-only, with UPSTREAM.md
        └── v1/                               this project's contracts for the target, same shape as project/v1
```

<!-- END AUTO-GENERATED contracts/README.md#layout -->

Referenced from root: `pnpm-workspace.yaml` (`packages`), `pnpm-lock.yaml` (`importers`), `.github/workflows/ci.yml` (`contracts`), `justfile` (`check_contracts`), `tools/conformance/`, `docs/mcp-tools.md` (`fit.schema.yaml`, `audience.schema.yaml`, `fit-record.schema.yaml` and `fit-record-update.schema.yaml` links).

### runtime

<!-- BEGIN AUTO-GENERATED runtime/README.md#layout -->

```text
runtime/
├── README.md
├── pyproject.toml                   package knowledge-mcp, command kb, knowledge-bus pin; ships knowledge-bus/ and skills/ in the package
├── requirements.lock                hashed export of uv.lock; the installed plugin runs from it
├── .claude-plugin/plugin.json       Claude Code manifest; declares the stdio server
├── .codex-plugin/plugin.json        Codex manifest
├── codex-mcp.json                   Codex's stdio server declaration
├── .gitignore
├── knowledge_mcp/
│   ├── cli.py                       kb: mcp, setup, fit, kbp, doctor, --version
│   ├── main.py                      build_server() and the stdio server
│   ├── __main__.py                  python -m knowledge_mcp: the stdio server
│   ├── hosts.py                     each agent app's settings file, skills folder and command line
│   ├── setup.py                     kb setup, kb setup --remove and kb doctor, with their state file
│   ├── configedit.py                adds and removes one entry in a JSON or TOML settings file
│   ├── localfit.py                  kb fit: reads a local file's folder chain and calls kb_fit
│   ├── start.py                     both manifests start this: builds the hash-checked environment, then runs knowledge_mcp
│   ├── contract.py                  what a host sends: folders and universe specs in scope
│   ├── scope.py                     rebuilds those folders in a private temporary folder
│   ├── bundled.py                   the bundled universe specs and skills, and their ref
│   ├── kbp.py                       runs the installed kbp console script
│   ├── fit.py                       matches a file name and folder against document types
│   ├── audience.py                  reads the audience frame from kbp --inspect output
│   ├── edits.py                     the edit record, in the state folder
│   ├── record.py                    the fit record: reads, merges and returns its text
│   ├── mark.py                      reads element questions from kbp --card output, for kb_mark
│   ├── passages.py                  splits an outside document's text into passages
│   ├── log.py                       one JSON Lines entry per answer, in the state folder
│   └── tools/                       kb_fit, kb_audience, the edit record tools, kb_fit_record, kb_mark, one tool per kbp mode
├── knowledge-bus/                   copied by `just refresh_knowledge_model` (never edit)
│   ├── UPSTREAM.md                  ref, date, and SHA-256 of every copied file
│   └── universes/<id>/              the bundled universe specs
├── skills/kb-*/                     knowledge-bus's skills, copied as is (never edit)
├── skills/km-write/SKILL.md         knowledge-mcp's own skill: the checks before writing
├── skills/km-fit-record/SKILL.md    knowledge-mcp's own skill: keeping the fit record
├── skills/km-bring-in/SKILL.md      knowledge-mcp's own skill: bringing in an outside document
├── scripts/generate_tools_doc.py    writes or checks the intro and the tool tables in a tools doc
└── tests/
    ├── hosts.py                     knowledge-base fixtures and what a host sends for them
    ├── record_host.py               a knowledge base, local or content only, and a host keeping its fit record
    ├── test_fit_end_to_end.py       kb_fit through the stdio server
    ├── test_kb_end_to_end.py        kb setup and --remove for every host, kb fit, kb mcp, kb kbp, kb doctor, the built package
    ├── test_configedit.py           one entry in and out of JSON and TOML settings, byte for byte
    ├── test_audience.py             kb_audience on both bundled universe specs
    ├── test_edits.py                recording, listing and undoing an edit
    ├── test_fit_record_end_to_end.py  the fit record across sessions and simultaneous chats
    ├── test_fit_record.py           the fit record's merge rules
    ├── test_mark_end_to_end.py      kb_mark on a pasted chat thread and a document at a Drive link
    ├── test_passages.py             passage boundaries
    ├── test_tools.py                the tool list: nothing commits, pushes or posts
    ├── test_kbp_tools.py            each kbp tool against kbp run directly
    ├── test_log.py
    ├── test_plugin.py               the folder copied alone, started from each manifest
    ├── test_fit.py
    └── test_scope.py
```

<!-- END AUTO-GENERATED runtime/README.md#layout -->

Referenced from root: `pyproject.toml` (`[tool.uv.workspace] members`), `uv.lock`, `ruff.toml` (`extend-exclude`, `known-first-party = ["knowledge_mcp"]`), `.github/workflows/ci.yml` (`runtime`), `justfile` (`check_runtime`, `generate_knowledge_mcp_lock`, `check_knowledge_mcp_lock`, `refresh_knowledge_model`, `generate_mcp_tools_doc`, `check_mcp_tools_doc`, `build_knowledge_mcp`, `generate_formula`), `.github/workflows/release.yml` (builds the package and its formula), `tools/formula/` (reads `runtime/requirements.lock` and `runtime/pyproject.toml`), `docs/mcp-tools.md` (generated intro and tool tables), `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` (`./runtime`), `tools/knowledge-model/`, `.prettierignore` and `.markdownlint-cli2.jsonc` (`runtime/knowledge-bus/universes/`, `runtime/skills/kb-*/`; `km-*` skills are checked), `renovate.json` (`mcp` and `knowledge-bus` rules; `pydantic` and `pytest` groups), `SECURITY.md` (`runtime/`), `docs/release-check.md` (`kb` commands).

## Related Projects

- [knowledge-bus](https://github.com/SterlingJF/knowledge-bus): the universe specs, skills and `kbp` checker knowledge-mcp carries.
