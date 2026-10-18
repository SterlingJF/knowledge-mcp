# Changelog

## 0.3.0

### Added

- `kb doctor` and `kb type` accept `--json`.
- `kb --version` prints the knowledge-bus version on a second line.
- The README gives [shell completion](README.md#shell-completion) steps for zsh, Bash and Fish.
- The `kb_*` tools publish `outputSchema` and return validated `structuredContent`.
- The `kb_*` tools and argument validation return RFC 9457 problem details with a `type` URI. Non-zero `kbp_*` exits preserve kbp output.
- Session-start reviews show new, moved and deleted files with filing assessments, unresolved document types and complete counts in a 50-file preview.
- `kb_prepare_document_moves` prepares a whole list of accepted moves at once and repairs the links between notes that move together.
- An accepted list can be undone from the edit records; an undo that conflicts with a later change stops and lists the affected files.
- Two moves to the same path, or a move into a path another file needs, block the list and name each affected move.
- A team folder keeps its own conventions and takes from the parent folder only the conventions it lists in `from_parent`.
- The agent can list the conventions in effect for a folder, with the folder each convention comes from.
- Filing proposals and moves block when the destination's universe specs lack the document type or define it differently.
- `kb_list_convention_templates` lists the ACE, PARA and Johnny.Decimal templates with their published sources, offline.
- The skills take the person through each convention a template proposes before the agent saves it.
- `kb_prepare_conventions` prepares the conventions file: a folder and a name pattern per document type.
- Filing proposals follow a saved convention and list any value the agent still has to supply.
- `kb type --filing-values` takes the values a convention needs.
- `kb_get_document_type` and `kb_prepare_document_types` answers include `filing`: a proposed folder and name, based on where files of the same document type already live.
- `kb_prepare_document_move` prepares an accepted move or rename, with the new text of every note whose links change. An ambiguous link blocks the move.
- `kb type` shows the proposed folder and name.

### Changed

- `kb fit <file>` is now `kb type <path>`.
- `--hat` is now `--role`, and `--top` is now `--root`.
- `kb kbp --<mode>` is now `kb kbp <mode>`, including `kb kbp validate`.
- MCP tool `kb_fit` is now `kb_get_document_type`.
- MCP tool `kb_audience` is now `kb_list_audiences`.
- MCP tool `kb_mark` is now `kb_prepare_import`.
- MCP tool `kb_edits` is now `kb_list_edits`.
- MCP tool `kb_fit_record` is now `kb_prepare_document_types`.
- MCP tool `kbp_check` is now `kbp_validate`.
- The `kb_get_document_type` argument `hat` is now `role`.
- Skill `km-write` is now `kb-write-document`.
- Skill `km-fit-record` is now `kb-track-document-types`.
- Skill `km-bring-in` is now `kb-import-document`.
- For a 0.2.1 `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, `kb_prepare_document_types` returns `document-types.yaml` text for the agent to save.
- The document-types schema is now `knowledge-mcp/document-types/1`, replacing `knowledge-mcp/fit-record/1`.
- In the document-types file, `kind` is now `document_type`.
- In the document-types file, `no_fit` is now `no_document_type`.
- In the document-types file, `made: fit|correction` is now `set_by: agent|person`.
- In document-types and edit records, `allowed_by.basis` renames `line` to `instruction` and `change_row` to `accepted_change`.
- In edit records, `basis`, `basis_text` and `basis_location` become `allowed_by.basis`, `allowed_by.text` and `allowed_by.location`.
- kb reports its own errors on stderr with an `Error:` line and a next step.
- kb reports its own usage errors with exit code 2 and suggests close matches. Arguments after `kb kbp <mode>` retain kbp errors and exit codes.
- `kb setup` and `kb setup --remove` print status lines and next steps on stderr.
- `kb doctor` prints one status line for the install and one per harness, then a fix for each problem or warning.
- Maintainers: `just format` now formats Python and the justfile.
- Maintainers: `just check` adds strict Python type checks, dead code detection, and checks for TOML, shell scripts, workflows, relative links and vendored files.
- Maintainers: the pre-commit hook checks large files and validates Renovate settings. When `uv.lock` changes, the hook refreshes `runtime/requirements.lock`.

### Fixed

- kb rejects a shortened flag, such as `kb setup --remov`, with exit code 2 instead of running the removal.
- `kb kbp --help` and `kb kbp -h` print help.
- On a broken install, kb prints an error and the reinstall command instead of a traceback.

## 0.2.1

### CLI

- Clarify command help and group setup output into registration details, skills and next steps.
- Show installation and registration check results with `kb doctor`. Use `kb doctor --verbose` for versions, configuration paths and the bundled guidance and skills.
- Show the app and folder in duplicate-skill warnings; keep the skill names in verbose output.
- Show the ZIP upload steps for Claude desktop skills.

### Release preparation

- Update package and plugin versions and lockfiles with `just release_prepare <version>`.
- Validate the matching changelog entry before creating a release or uploading a new source archive.
- Use that changelog entry for the published release notes.

### Homebrew bottles

- Add native ARM64 and Intel macOS bottles with source fallback and install checks before updating the tap. The workflow also supports adding bottles to the existing `v0.2.0` release without changing its version or tag.

## 0.2.0

knowledge-mcp now provides a local stdio MCP server and the `kb` CLI. Your agent can look up each file's purpose using the document definitions for your knowledge base. One install includes knowledge-bus, which supplies the document definitions, tools and skills.

### Install and setup

- Install with `brew install sterlingjf/tap/knowledge-mcp`. Homebrew builds knowledge-mcp and knowledge-bus from source.
- Connect an agent app with `kb setup <host>`. Setup adds the server to the app's settings and links the `kb-*` and `km-*` skills into the app's skills folder. `brew upgrade` refreshes the linked skills.

| App                                                             | Host             |
| --------------------------------------------------------------- | ---------------- |
| Claude Code                                                     | `claude-code`    |
| Codex, including the ChatGPT desktop app's Codex and Work modes | `codex`          |
| Claude desktop app                                              | `claude-desktop` |
| Pi                                                              | `pi`             |
| OpenCode                                                        | `opencode`       |

- Claude Code and Codex also support installation as a plugin from this repository's marketplace.
- Disconnect each app with `kb setup --remove <host>`, then uninstall with `brew uninstall knowledge-mcp`. Removal reverses only the changes made by setup. The answer log and edit record remain in the state folder. After disconnecting the last app, `kb setup --remove` prints the state folder's path and the `KNOWLEDGE_MCP_STATE_DIR` variable name.

### Commands

- `kb mcp` runs the server. Each app starts the server over stdio for a session. The server opens no listening port and runs only during the session.
- `kb fit <file>` identifies a local file's purpose from the terminal.
- `kb kbp` runs the knowledge-bus `kbp` command unchanged.
- `kb doctor` checks knowledge-bus, bundled Knowledge Bus specifications, skills and each agent app. It also shows `KNOWLEDGE_MCP_STATE_DIR` and the state folder in use.

### Tools

- `kb_fit` returns every matching specification and document type based on the file's path, name and folder. If no document type matches, `kb_fit` lists all types from the applicable specifications. Saved classifications in the fit record take priority over automatic matches.
- `kb_audience` lists the readers defined for a document type in that type's specification.
- `kb_record_edit` records each agent edit, the request or standing instruction that authorized the edit, and the original text. `kb_edits` lists a file's recorded edits for review or undo.
- `kb_fit_record` prepares classification updates for files that were created, moved or deleted. Your corrections take priority over agent guesses.
- `kb_mark` splits an external document into passages and lists predefined questions for labeling those passages.
- knowledge-mcp exposes each knowledge-bus CLI mode as a `kbp_*` tool: check, self-check, version, mint, inspect, explore, kinds and card. Each tool returns the `kbp` command's output unchanged.

### Skills

- `km-write`: identifies the document type and reads its writing guidance. Your agent presents each condition from the guidance as a guess for you to confirm. The agent then asks who the document is for before writing.
- `km-fit-record`: your agent updates saved document types and readers after creating, moving or deleting files.
- `km-bring-in`: matches passages from an external document to your notes and identifies unmatched material. Your agent files passages only after your approval.
- knowledge-bus skills come with the install, including `kb-check`, `kb-explore`, `kb-ingest` and `kb-evolve`. Your agent uses bundled document definitions when the file's parent folders contain no `.knowledge-bus/` configuration directory.

### Records

- The fit record stores each file's specification, document type (or "no fit") and intended reader at `.knowledge-bus/plugins/knowledge-mcp/record.yaml`. Your agent updates the record with its own file tools. knowledge-mcp writes nothing in your knowledge base.
- The state folder stores the answer log (every answer) and the edit record (every recorded edit). The state folder's location is selected in this order:

  1. `$KNOWLEDGE_MCP_STATE_DIR`, when set.
  2. `$XDG_STATE_HOME/knowledge-mcp`, when `XDG_STATE_HOME` is set.
  3. `~/.local/state/knowledge-mcp`.

  Codex receives `KNOWLEDGE_MCP_STATE_DIR` and `XDG_STATE_HOME` through its MCP entry's `env_vars` list. For other apps, set the chosen variable in the environment used to launch the app.

### Removed

- The desktop menu-bar app.
- The vault engine, its HTTP API and its local ports.
- The twelve tools that listed, read and changed vault files and artifacts through the engine.

### Migrate from the desktop app

Quit the old desktop app and remove each agent app's `knowledge-mcp` entry for `http://127.0.0.1:17952/mcp` before running `kb setup`. Setup refuses to overwrite a `knowledge-mcp` entry configured for another server.
