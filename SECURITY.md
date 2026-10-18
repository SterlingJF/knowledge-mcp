# Security Policy

## Supported Versions

Only the latest release gets security fixes.

## Reporting a Vulnerability

Report vulnerabilities privately at https://github.com/SterlingJF/knowledge-mcp/security/advisories/new. Include the affected version, steps to reproduce, and the impact. Do not open a public issue.

## Scope

### In Scope

- The `kb` command, the MCP server, and the `runtime/` plugin folder with its manifests
- The settings entries, skill links and backups that `kb setup` writes and `kb setup --remove` deletes
- The Homebrew formula from the release workflow
- The marketplace files `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`
- The justfile, the Husky and pre-commit hooks, `tools/` and `.github/workflows/`

### Out of Scope

- Claude Code, Codex, the Claude desktop app, Pi, OpenCode, Homebrew and uv
- The knowledge-bus package and its bundled universe specs
- The six skills copied from knowledge-bus: kb-check, kb-evolve, kb-explore, kb-ingest, kb-uncover-question and kb-uncover-decision
- Other processes running as your user

Report vulnerabilities in the knowledge-bus package, its universe specs or the copied skills to [knowledge-bus](https://github.com/SterlingJF/knowledge-bus).

## Trust Model

The harness starts the MCP server over stdio. The server opens no network port, makes no network call and opens no file in your knowledge base. Your agent reads the files and passes their text to the tools as arguments. `kb type` reads the `.knowledge-bus/` folders from the root down to the file's folder, and the document-types file.

The Claude Code and Codex plugins start the server through uv. uv downloads Python 3.14 when it is missing. The launcher reuses an environment for the same lockfile and Python version, or asks uv to build an environment from `runtime/requirements.lock`. uv downloads packages missing from its cache. `kb setup` registers the installed `kb mcp` command instead.

kb uses `$KNOWLEDGE_MCP_STATE_DIR` when the path is absolute after `~` expansion. Otherwise, kb uses `$XDG_STATE_HOME/knowledge-mcp` when the XDG path is absolute after `~` expansion. The fallback is `~/.local/state/knowledge-mcp`. kb creates `log.jsonl`, `edits.jsonl` and `setup/state.json` with mode 0600. Keep the state folder outside every knowledge base.

| File                           | Location                                                                                                                    | Contents                                                                                                                                    | Written by                                           |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| `log.jsonl`                    | State folder                                                                                                                | Tool answers and argument digests                                                                                                           | The MCP server, `kb type`                            |
| `edits.jsonl`                  | State folder                                                                                                                | Replaced text, replacement text or its digest, and edit metadata ([fields](contracts/extensions/mcp/v1/edits.schema.yaml))                  | `kb_record_edit`                                     |
| `explorer/`                    | State folder                                                                                                                | Offline HTML viewers for universe specs. A call with the same `folders`, `.knowledge-bus/` texts and `universe` replaces the earlier viewer | `kbp_explore`                                        |
| `setup/state.json`             | State folder                                                                                                                | Settings entries, skill links, backup paths and created folders                                                                             | `kb setup`                                           |
| `setup/backups/`               | State folder                                                                                                                | Copies of harness settings files before `kb setup` edits them                                                                               | `kb setup`                                           |
| `knowledge-mcp-*/`             | System temporary folder (mode 0700)                                                                                         | Copies of the universe specs and `workspace.yaml` files that kbp reads, deleted after each call and at exit                                 | The MCP server, `kb type`                            |
| `document-types.yaml`          | `.knowledge-bus/plugins/knowledge-mcp/` in the knowledge base                                                               | Document type, reader and permission per file ([fields](contracts/extensions/mcp/v1/document-types.schema.yaml))                            | Your agent                                           |
| Settings entry and skill links | Each harness's settings file and skills folder (the Claude desktop app has no skills folder)                                | One `knowledge-mcp` entry, one link per skill                                                                                               | `kb setup`                                           |
| Plugin environment             | `$XDG_CACHE_HOME/knowledge-mcp/environments` when `$XDG_CACHE_HOME` is absolute, else `~/.cache/knowledge-mcp/environments` | Python environments built from `runtime/requirements.lock`, with each downloaded package hash-checked                                       | uv, run by `knowledge_mcp.start` in a plugin install |

## Known Limitations

- kb never deletes lines from `log.jsonl` or `edits.jsonl`. `kbp_explore` replaces existing viewers but retains viewers for other inputs.
- kb trusts the agent's arguments. kb cannot confirm that the folder names, universe spec texts and edit texts match your files, or that an `allowed_by` value matches what you said.
- If two harness sessions save `document-types.yaml` at once, the later save can overwrite the other session's entries.
- An imported document can hold instructions aimed at your agent. The `kb-import-document` skill tells the agent to treat every passage as data, never as instructions.
- `brew uninstall` leaves the settings entries, skill links and `setup/` in place. Run `kb setup --remove <harness>` for each harness before `brew uninstall`.
- For Claude Code and Pi, `kb setup` uses the corresponding CLI when available. kb makes no settings backup during CLI registration.
- CI runs no vulnerability scan.
- The pre-push and post-merge hooks scan the lockfiles and skip the advisories listed in `osv-scanner.toml`.
- The hooks warn and continue only when the scan exits with code 127 and reports a recognized OSV connection error.
