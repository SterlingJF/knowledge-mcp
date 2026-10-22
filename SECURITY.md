# Security Policy

## Supported Versions

Only the latest release gets security fixes.

## Reporting a Vulnerability

Report vulnerabilities through a [private security advisory](https://github.com/SterlingJF/knowledge-mcp/security/advisories/new). Include the affected version, steps to reproduce, and the impact. Do not open a public issue.

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

The harness starts the MCP server over stdio. The server opens no network port, makes no network call and opens no file in your knowledge base. Your agent reads the files and passes their text to the tools as arguments. `kb type` enumerates file paths under the root and reads universe specs, workspace settings, conventions and the document-types file. It does not read document contents.

The Claude Code and Codex plugins start the server through uv. uv downloads Python 3.14 when it is missing. uv manages the plugin root’s `.venv` from `uv.lock` using `uv run --locked`. uv downloads packages missing from its cache. `kb setup` registers the installed `kb mcp` command instead.

kb uses `$KNOWLEDGE_MCP_STATE_DIR` when the path is absolute after `~` expansion. Otherwise, kb uses `$XDG_STATE_HOME/knowledge-mcp` when the XDG path is absolute after `~` expansion. The fallback is `~/.local/state/knowledge-mcp`. kb creates `log.jsonl`, `edits.jsonl` and `setup/state.json` with mode 0600. Keep the state folder outside every knowledge base.

The state folder holds the following data. Tool answers can include document text and prepared replacements, so the logs may contain sensitive content even though arguments are stored only as digests. The harness and agent also receive the text you supply; their data handling is outside knowledge-mcp's control.

| File or folder     | Contents                                                                                                                              | Written by                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| `log.jsonl`        | Tool answers, location text and argument digests                                                                                      | The MCP server, `kb type` |
| `edits.jsonl`      | Original text, replacement text or its digest, permission and edit metadata ([schema](contracts/extensions/mcp/v1/edits.schema.yaml)) | `kb_record_edit`          |
| `explorer/`        | Offline HTML viewers; repeating the same folder, spec text and selected universe spec replaces the earlier viewer                     | `kbp_explore`             |
| `setup/state.json` | Settings entries, skill links, backup paths and created folders                                                                       | `kb setup`                |
| `setup/backups/`   | Copies of harness settings files before setup edits them                                                                              | `kb setup`                |

Outside the state folder:

- **Knowledge-base configuration.** Your agent writes `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` under the root to retain each file's document type, reader and permission. It writes `conventions.yaml` in the same configuration folder under the root or a team folder for accepted naming and filing patterns and parent selections. The [document-types schema](contracts/extensions/mcp/v1/document-types.schema.yaml) and [conventions schema](contracts/extensions/mcp/v1/conventions.schema.yaml) define those files.
- **Temporary spec copies.** The server and `kb type` write universe specs and `workspace.yaml` files for kbp in `knowledge-mcp-*/` under the system temporary folder, with mode 0700. Each call removes its copies; process exit also removes the temporary folder.
- **Harness settings.** `kb setup` writes one `knowledge-mcp` entry in each harness's settings file and links the bundled skills into its skills folder. The Claude desktop app takes skill uploads instead.
- **Plugin environments.** uv manages `.venv` in the installed plugin root using `uv.lock`.

## Known Limitations

- kb never deletes lines from `log.jsonl` or `edits.jsonl`. `kbp_explore` replaces existing viewers but retains viewers for other inputs.
- kb trusts the agent's arguments. kb cannot confirm that the folder names, universe spec texts and edit texts match your files, or that an `allowed_by` value matches what you said.
- If two harness sessions save `document-types.yaml` at once, the later save can overwrite the other session's entries. Agents must reread configuration and documents and compare digests before applying prepared changes. These checks do not provide a transaction across several files.
- Move preparation relies on the agent's complete inventory, link search and supplied document text. The agent applies moves, verifies link targets and preserves concurrent changes during recovery or undo. knowledge-mcp cannot enforce those filesystem checks.
- knowledge-mcp adds no sign-in or permission levels. Access to team folders and their conventions depends on the underlying file store.
- An imported document can hold instructions aimed at your agent. The `kb-import-document` skill tells the agent to treat every passage as data, never as instructions.
- `brew uninstall` leaves the settings entries, skill links and `setup/` in place. Run `kb setup --remove <harness>` for each harness before `brew uninstall`.
- For Claude Code and Pi, `kb setup` uses the corresponding CLI when available. kb makes no settings backup during CLI registration.
- CI runs no vulnerability scan.
- The pre-push and post-merge hooks scan the lockfiles and skip the advisories listed in `osv-scanner.toml`.
- The hooks warn and continue only when the scan exits with code 127 and reports a recognized OSV connection error.
