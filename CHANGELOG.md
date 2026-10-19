# Changelog

## 0.3.0

### Added

- Naming and filing proposals follow saved conventions or the folders holding files of the same document type. `kb type` shows the proposed name and folder; `--filing-values` supplies values read from the document.
- Conventions can start from existing folders, from scratch, or from offline ACE, PARA and Johnny.Decimal templates with published sources. The agent reviews each proposal with you and saves accepted patterns using `kb_prepare_conventions`.
- Team folders keep their own conventions and explicitly select parent conventions. `kb_list_conventions` shows which conventions apply and where each comes from.
- At session start, review new, moved and deleted files, their proposed names and folders, and files still needing a document type. Reviews show totals and preview up to 50 files.
- `kb_prepare_document_move` and `kb_prepare_document_moves` prepare accepted moves and link repairs from agent-supplied documents. Preparation blocks conflicting destinations, incompatible document types and ambiguous or unsupported links. The agent applies and records the changes; undo can restore a whole list and stops if later edits conflict.
- `kb doctor` and `kb type` accept `--json`. The `kb_*` tools publish `outputSchema`, return validated `structuredContent`, and use RFC 9457 problem details for errors. Non-zero `kbp_*` exits preserve kbp output.
- Shell completion is available for zsh, Bash and Fish; see the [setup steps](README.md#shell-completion).

### Changed

- Update bundled MCP SDK to 2.2.0.
- CLI migration: `kb fit <file>` becomes `kb type <path>`, `--hat` becomes `--role`, and `--top` becomes `--root`. Use `kb kbp <mode>` instead of `kb kbp --<mode>`, including `kb kbp validate`. Arguments after the mode retain upstream grammar, output and exit codes.
- Renamed MCP tools as follows. The former `hat` argument to `kb_get_document_type` is now `role`.

| Previous tool   | Replacement                 |
| --------------- | --------------------------- |
| `kb_fit`        | `kb_get_document_type`      |
| `kb_audience`   | `kb_list_audiences`         |
| `kb_mark`       | `kb_prepare_import`         |
| `kb_edits`      | `kb_list_edits`             |
| `kb_fit_record` | `kb_prepare_document_types` |
| `kbp_check`     | `kbp_validate`              |

- Skill migration: `km-write` → `kb-write-document`, `km-fit-record` → `kb-track-document-types`, and `km-bring-in` → `kb-import-document`.
- `kb_prepare_document_types` converts a 0.2.1 `.knowledge-bus/plugins/knowledge-mcp/record.yaml` to `document-types.yaml` text for the agent to save. The schema changes from `knowledge-mcp/fit-record/1` to `knowledge-mcp/document-types/1`; `kind` becomes `document_type`, `no_fit` becomes `no_document_type`, and `made: fit|correction` becomes `set_by: agent|person`.
- Edit answers use `knowledge-mcp/edit/2` and `knowledge-mcp/edits/2`, with optional operation metadata for whole-list undo. Legacy ungrouped edit records remain readable. Edit permission fields `basis`, `basis_text` and `basis_location` move under `allowed_by` as `basis`, `text` and `location`. In document-types and edit records, basis values `line` and `change_row` become `instruction` and `accepted_change`.
- CLI errors go to stderr with an `Error:` line and a next step. Usage errors exit 2 and suggest close matches. Setup and removal report status and next steps on stderr; doctor reports the install and each harness with fixes for problems and warnings. `kb --version` prints the knowledge-bus version on a second line.
- Maintainer checks now include strict Python typing, dead code detection, TOML, shell scripts, workflows, relative links and vendored-file integrity. `just format` includes Python and the justfile. Pre-commit checks large files and Renovate settings, and refreshes `runtime/requirements.lock` when `uv.lock` changes.

### Fixed

- Shortened flags such as `kb setup --remov` fail with exit code 2 instead of running the removal.
- `kb kbp --help` and `kb kbp -h` print help.
- Broken installs report an error and a reinstall command instead of a traceback.

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
