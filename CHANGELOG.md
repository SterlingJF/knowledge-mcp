# Changelog

## Unreleased

### Homebrew bottles

- Add native ARM64 and Intel macOS bottles with source fallback and install checks before updating the tap. The workflow also supports adding bottles to the existing `v0.2.0` release without changing its version or tag.

## 0.2.0 (unreleased)

Knowledge-MCP now provides a local stdio MCP server and the `kb` CLI. Your agent can look up each file's purpose using the document definitions for your knowledge base. One install includes knowledge-bus, which supplies the document definitions, tools and skills.

### Install and setup

- Install with `brew install sterlingjf/tap/knowledge-mcp`. Homebrew builds Knowledge-MCP and knowledge-bus from source.
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
- Knowledge-MCP exposes each knowledge-bus CLI mode as a `kbp_*` tool: check, self-check, version, mint, inspect, explore, kinds and card. Each tool returns the `kbp` command's output unchanged.

### Skills

- `km-write`: identifies the document type and reads its writing guidance. Your agent presents each condition from the guidance as a guess for you to confirm. The agent then asks who the document is for before writing.
- `km-fit-record`: your agent updates saved document types and readers after creating, moving or deleting files.
- `km-bring-in`: matches passages from an external document to your notes and identifies unmatched material. Your agent files passages only after your approval.
- knowledge-bus skills come with the install, including `kb-check`, `kb-explore`, `kb-ingest` and `kb-evolve`. Your agent uses bundled document definitions when the file's parent folders contain no `.knowledge-bus/` configuration directory.

### Records

- The fit record stores each file's specification, document type (or "no fit") and intended reader at `.knowledge-bus/plugins/knowledge-mcp/record.yaml`. Your agent updates the record with its own file tools. Knowledge-MCP writes nothing in your knowledge base.
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
