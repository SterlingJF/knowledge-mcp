# Knowledge-MCP

## What is Knowledge-MCP?

**Opinionated MCP/API for your notes.** Pick a folder, connect your agents, and keep your notes organized. It's free, extensible, and works completely offline.

Inspired by @nickmilo's [ACE folder system](https://forum.obsidian.md/t/the-ultimate-folder-system-a-quixotic-journey-to-ace/63483), Knowledge-MCP runs in the background and serves the folders you choose locally without sending data to the cloud.

The goal is to keep knowledge clear and organized for agents and humans.

- **Clear** — minimizes agent context and human effort when retrieving or classifying knowledge.
- **Organized** — follows a repeatable structure that agents and humans can recognize.

## Features

- **Opinionated folder system at the vault's base:** Six main folders — `+`, `x`, `Atlas`, `Calendar`,
  `Efforts`, `.knowledge-mcp`. (See [vault-ace-structure.md](./docs/vault-ace-structure.md))
- **File access:** Every file in the five content folders is visible.
- **Knowledge model overlays:** Knowledge-MCP tools let you codify additional file structure and semantics.
- **Guided interaction:** Skills, tools, and endpoints — all revolving around folder system and knowledge model awareness — guide agents and automations as you work.
- **Contextual feedback:** Agents get feedback and errors driven by awareness of how folders, files, and file contents are organized.

The process is entirely local:

- Two loopback listeners (API 17951, MCP 17952) and zero outbound network calls.
- Runs on macOS (Apple Silicon).

## Known Limits

- The MCP server serves one protocol revision, named in [MCP tools](./docs/mcp-tools.md), and refuses every other revision.
- Serving is all-or-nothing from the tray; there is no per-vault or MCP-only toggle yet.
- Knowledge models are selected globally at startup; automatic discovery and live per-vault
  loading of knowledge-bus `<folder>-spec/` outputs has not shipped yet.

## Install

[Download the latest release](https://github.com/SterlingJF/knowledge-mcp/releases/latest).

## Quick Start

1. **Launch** Knowledge-MCP.
2. **Add** a folder (or create a fresh vault).
3. **Register** the endpoint using one of the client configurations below.

### Connect a Client

The service listens at `http://127.0.0.1:17952/mcp`.

Client-specific setup:

#### Claude Code

```bash
claude mcp add --transport http knowledge-mcp http://127.0.0.1:17952/mcp
```

#### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{ "mcpServers": { "knowledge-mcp": { "url": "http://127.0.0.1:17952/mcp" } } }
```

#### Claude Desktop

Claude Desktop's connectors dial from Anthropic's cloud, which cannot reach `127.0.0.1`, and its
local config is stdio-only — bridge with [mcp-remote](https://github.com/geelen/mcp-remote)
(community tool) in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowledge-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:17952/mcp"]
    }
  }
}
```

#### Other Clients

| Client     | Config file                           | Entry                                                                                                                           |
| ---------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Codex      | `~/.codex/config.toml`                | `[mcp_servers.knowledge-mcp]` then `url = "http://127.0.0.1:17952/mcp"` — recent Codex; older builds need the mcp-remote bridge |
| OpenCode   | `opencode.json`                       | `"knowledge-mcp": { "type": "remote", "url": "http://127.0.0.1:17952/mcp", "enabled": true }` under `"mcp"`                     |
| Windsurf   | `~/.codeium/windsurf/mcp_config.json` | `"knowledge-mcp": { "serverUrl": "http://127.0.0.1:17952/mcp" }`                                                                |
| Zed        | `settings.json`                       | `"context_servers": { "knowledge-mcp": { "url": "http://127.0.0.1:17952/mcp" } }`                                               |
| Gemini CLI | `~/.gemini/settings.json`             | `"knowledge-mcp": { "httpUrl": "http://127.0.0.1:17952/mcp" }` — the field is `httpUrl`                                         |

## Project Map

A module is a workspace package, or a root folder whose README has a `## Layout` section. Its folder name is also its:

- CI job
- `check_<name>` recipe, run by `just check` (hyphens become underscores)
- package name
- README region below

To add, rename, or remove a module, change these names and the files in its "Referenced from root" line, then run `just generate_readme_maps`. `just check` fails when the names disagree.

### Root

```text
.
├── README.md
├── DESIGN.md                    visual identity; front matter generated from components/
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
├── .github/workflows/ci.yml
├── .gitignore
├── .prettierrc.json
├── .prettierignore
├── .markdownlint-cli2.jsonc
├── .oxlintrc.json               shared base, extended by modules
├── ruff.toml
├── .yamllint.yml
├── renovate.json
├── osv-scanner.toml
├── .evidence/README.md          local evidence archive; only the README is tracked
├── docs/                        product docs: HTTP API, MCP tools, vault structure, refused writes
├── skills/
├── tools/                       repo maintenance, one folder per tool
│   ├── modules/                 checks every module is wired the same way
│   ├── readme-regions/          fills the module maps below
│   ├── visual-tokens/           components tokens -> CSS, TS, DESIGN.md
│   ├── conformance/             checks contract samples
│   ├── dependencies/            scans the lockfiles for vulnerabilities
│   ├── placeholders/            checks no project-template placeholder is left
│   ├── ports/                   checks the loopback ports agree across modules
│   └── knowledge-model/         vendors the knowledge-bus files into contracts/
├── components/                  module
├── contracts/                   module
├── launcher/                    module
├── server/                      module
└── mcp-server/                  module
```

### components

<!-- BEGIN AUTO-GENERATED components/README.md#layout -->

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

<!-- END AUTO-GENERATED components/README.md#layout -->

Referenced from root: `pnpm-workspace.yaml` (`packages`), `pnpm-lock.yaml` (`importers`), `package.json` (`shadcn`), `.github/workflows/ci.yml` (`components`), `justfile` (`check_components`, `generate_visual_tokens`, `check_visual_tokens`, `add_shadcn_atoms`), `tools/visual-tokens/`, `DESIGN.md` (generated front matter, `components/design/visual-tokens.json`).

### contracts

<!-- BEGIN AUTO-GENERATED contracts/README.md#layout -->

```text
contracts/
├── README.md
├── package.json                              lint
├── redocly.yaml                              lint policy for every OpenAPI file
├── project/                                  this project's own modules talk to each other
│   └── v1/
│       ├── vault.rest.openapi.yaml           vault lifecycle on the engine's HTTP API
│       ├── <name>.rest.openapi.yaml          request / response
│       ├── <name>.realtime-sse.openapi.yaml  event stream
│       ├── <name>.schema.yaml                data shape
│       └── conformance/
│           ├── pass/<name>.<case>.yaml       must validate against <name>.schema.yaml
│           └── fail/<name>.<case>.yaml       must not validate
├── plugins/<name>/                           outside code plugs into this project
│   └── v1/                                   same shape as project/v1
└── extensions/                               this project reaches into another project
    ├── knowledge-bus/upstream/               protocol, universe, and type guidance, with UPSTREAM.md
    └── <target>/
        ├── upstream/                         the target's spec, vendored read-only, with UPSTREAM.md
        └── v1/                               this project's contracts for the target, same shape as project/v1
```

<!-- END AUTO-GENERATED contracts/README.md#layout -->

Referenced from root: `pnpm-workspace.yaml` (`packages`), `pnpm-lock.yaml` (`importers`), `.github/workflows/ci.yml` (`contracts`), `justfile` (`check_contracts`, `refresh_knowledge_model`, `check_server`, `build_sidecars`), `tools/conformance/`, `tools/knowledge-model/`, `.prettierignore` (`contracts/extensions/*/upstream/`), `docs/http-api.md` (vault contract link).

### launcher

<!-- BEGIN AUTO-GENERATED launcher/README.md#layout -->

```text
launcher/
├── README.md
├── package.json                   check
├── index.html
├── vite.config.ts                 dev server on port 1420; inlines the package version
├── tsconfig.json
├── .oxlintrc.json                 extends ../.oxlintrc.json
├── .oxfmtrc.json
├── prettier.config.js
├── .prettierignore
├── .gitignore
├── scripts/release-build.sh       signs, notarizes, and verifies the DMG; expects built sidecars
├── src/                           the window
│   ├── main.tsx
│   ├── App.tsx                    engine connection; renders VaultSwitcher from components
│   ├── styles.css                 imports components/styles.css
│   ├── globals.d.ts
│   └── lib/                       engine client and shell bridge, with tests
└── src-tauri/                     the Rust shell
    ├── Cargo.toml
    ├── Cargo.lock
    ├── build.rs                   checks the CSP allows the engine port and not the MCP port
    ├── tauri.conf.json            window, CSP, bundle, sidecars
    ├── capabilities/default.json  what the window may do
    ├── entitlements.plist
    ├── icons/
    ├── binaries/                  sidecars from `just build_sidecars`; git-ignored
    ├── src/main.rs
    ├── src/lib.rs                 tray, sidecar supervision, events
    ├── src/ports.rs               engine and MCP server ports
    └── .gitignore
```

<!-- END AUTO-GENERATED launcher/README.md#layout -->

Referenced from root: `pnpm-workspace.yaml` (`packages`), `pnpm-lock.yaml` (`importers`), `.github/workflows/ci.yml` (`launcher`), `justfile` (`check_launcher`, `build_launcher`, `release_launcher`, `build_sidecars`), `tools/ports/`, `.prettierignore` (`target/`, `**/gen/schemas/`), `renovate.json` (`tauri` group, `cargo` rule), `osv-scanner.toml` (`RUSTSEC` exceptions).

### server

<!-- BEGIN AUTO-GENERATED server/README.md#layout -->

```text
server/
├── README.md
├── pyproject.toml
├── km-server.spec               freezes dist/km-server; the caller names the knowledge-model folder
├── .gitignore
├── app/
│   ├── factory.py               create_app(): routers, middleware, error handlers, knowledge model
│   ├── settings.py              KM_* environment settings
│   ├── config.py                remembered vaults in ~/.config/knowledge-mcp/config.json
│   ├── context.py               who is asking: the local person or a declared agent
│   ├── dependencies.py          request dependencies
│   ├── errors.py                KmError -> {detail, errorCode, fields}
│   ├── roles.py                 routers per role
│   ├── api_models_auto.py       generated by datamodel-codegen (never edit)
│   ├── entrypoints/desktop.py   km-server entry point
│   ├── knowledge_model/         loads universes and guidance
│   ├── middleware/              request logging
│   ├── routers/                 artifacts, files, universes, vaults, storage, health
│   ├── store/                   artifact files: codec, file store, validation, vaults
│   ├── vault/                   vault folder layout
│   ├── types/url.py             URL validator for the generated models
│   └── utilities/               atomic writes, logging
└── tests/
    ├── conftest.py
    ├── test_artifacts_api.py
    ├── test_codec.py
    ├── test_config_and_storage.py
    ├── test_files_api.py
    ├── test_store_and_roles.py
    └── test_vault.py
```

<!-- END AUTO-GENERATED server/README.md#layout -->

Referenced from root: `pyproject.toml` (`[tool.uv.workspace] members`), `uv.lock`, `ruff.toml` (`extend-exclude`, `known-first-party = ["app"]`), `.github/workflows/ci.yml` (`server`), `justfile` (`check_server`, `build_sidecars`), `tools/ports/`, `renovate.json` (`fastapi`, `pydantic`, and `pytest` groups).

### mcp-server

<!-- BEGIN AUTO-GENERATED mcp-server/README.md#layout -->

```text
mcp-server/
├── README.md
├── pyproject.toml
├── km-mcp.spec                      freezes dist/km-mcp
├── .gitignore
├── app/
│   ├── server.py                    build_app(): the MCP server, its tools, and the front door
│   ├── front_door.py                refuses any request not on the served MCP revision
│   ├── km_api.py                    HTTP client for the engine
│   ├── errors.py                    engine errors -> advice for the agent
│   ├── settings.py                  KM_MCP_* environment settings
│   ├── api_models_auto.py           generated by datamodel-codegen (never edit)
│   ├── entrypoints/local.py         km-mcp entry point
│   ├── tools/                       artifacts, files, universes, vaults
│   └── types/url.py                 URL validator for the generated models
├── plugin/knowledge-mcp/            agent plugin manifest for this server
├── scripts/generate_tools_doc.py    writes or checks the intro and the tool tables in a tools doc
└── tests/
    ├── conftest.py
    ├── test_errors.py
    ├── test_front_door.py
    ├── test_km_api.py
    ├── test_port_declaration.py
    └── test_tools.py
```

<!-- END AUTO-GENERATED mcp-server/README.md#layout -->

Referenced from root: `pyproject.toml` (`[tool.uv.workspace] members`), `uv.lock`, `ruff.toml` (`extend-exclude`, `known-first-party = ["app"]`), `.github/workflows/ci.yml` (`mcp-server`), `justfile` (`check_mcp_server`, `generate_mcp_tools_doc`, `check_mcp_tools_doc`, `build_sidecars`), `docs/mcp-tools.md` (generated intro and tool tables), `tools/ports/`, `renovate.json` (`mcp` rule; `fastapi`, `pydantic`, and `pytest` groups), `SECURITY.md` (`mcp-server/plugin/`).

## Docs

- [API Reference](./docs/http-api.md): endpoints, headers, and environment variables.
- [MCP tools](./docs/mcp-tools.md): the tools agents call and the protocol revision the server serves.
- [Vault structure](./docs/vault-ace-structure.md): the six folders and what each holds.
- [How writes are refused](./docs/how-writes-are-refused.md): which agent writes are refused, and why.

## Roadmap

- Vault upkeep automation — scheduled hygiene the service performs for a watched vault.
- Scoped reads and a query surface.
- Configurable folder mapping for existing vault conventions.
- Dynamic knowledge-model discovery — load global and per-vault knowledge-bus `<folder>-spec/`
  outputs as they appear.
- Linux and Windows launchers.
- Per-vault serving controls and an MCP-only toggle.

## Contributing

Issues welcome; PRs by discussion first. Report vulnerabilities privately: see [SECURITY.md](./SECURITY.md).

### Development

Needs Node (`.node-version`), pnpm, uv, [just](https://just.systems/), and Rust. The pre-push and post-merge hooks also need osv-scanner.

```sh
just install_frozen
uv sync --locked --all-packages
```

`just install_frozen` also installs the Git hooks. Large-file check: `uv run pre-commit run --all-files`.

From the repo root:

| Command                              | Purpose                                                                      |
| ------------------------------------ | ---------------------------------------------------------------------------- |
| `just check`                         | Run every check CI runs; changes nothing                                     |
| `just build_sidecars`                | Check the ports, then freeze the engine and the MCP server into the launcher |
| `just build_launcher`                | Build the sidecars, then the app and DMG                                     |
| `just release_launcher`              | Build the sidecars, then a signed, notarized, and verified DMG               |
| `just generate_mcp_tools_doc`        | Write the intro and the tool tables in `docs/mcp-tools.md`                   |
| `just refresh_knowledge_model <ref>` | Vendor the knowledge-bus files at `<ref>` into `contracts/`                  |
| `just generate_visual_tokens`        | Generate the token CSS and TypeScript, and the DESIGN.md front matter        |
| `just generate_readme_maps`          | Fill the module maps above                                                   |
| `just scan_dependencies`             | Scan the lockfiles with OSV                                                  |

Each module's README lists its own commands.

## License

MIT License — see [LICENSE](LICENSE).

The code is open source; the Knowledge-MCP name and branding are not. Forks should use their own identity and not imply affiliation.

## Related Projects

- [knowledge-bus](https://github.com/SterlingJF/knowledge-bus) - The knowledge schema used. knowledge-bus structures your knowledge; knowledge-mcp structures your vault and serves it to agents.

## Credits

- Folder shape inspired by Nick Milo's ACE framework (Atlas / Calendar / Efforts) —
  [the forum post](https://forum.obsidian.md/t/the-ultimate-folder-system-a-quixotic-journey-to-ace/63483).
- The plain-files-for-agents stance follows Andrej Karpathy's
  [append-and-review note](https://karpathy.bearblog.dev/the-append-and-review-note/) (2025) and
  [LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026).
