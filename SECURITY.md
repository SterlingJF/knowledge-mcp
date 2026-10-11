# Security Policy

## Trust Model

knowledge-mcp runs on your computer. Homebrew installs the `kb` command, and `kb setup` registers the MCP server with Claude Code, Codex, the Claude desktop app, Pi or OpenCode; Claude Code and Codex can also install the server as a plugin. The agent app starts the server over stdio for each session with `kb mcp`, or from the plugin folder; the server opens no network port and listens for nothing, and nothing of knowledge-mcp runs between sessions.

The server opens no file of your knowledge base. Your agent reads the files, through its own tools or a connector, and sends the server what each tool asks for: a file's name and location as text, its folders, and the headers or text of the universe spec files on its path. The server writes those universe spec files into a private temporary folder, runs knowledge-bus's `kbp` there, and removes the folder after each call.

The server makes no network call. The host's model reads what your agent reads, under the host's terms.

Every answer adds one line to `log.jsonl` in knowledge-mcp's state folder: `$KNOWLEDGE_MCP_STATE_DIR` when set, else `$XDG_STATE_HOME/knowledge-mcp`, else `~/.local/state/knowledge-mcp`. Each line holds the time, the tool, the location text, a SHA-256 digest of the arguments, and every text returned, which can include the text of your universe specs. kb creates the folder readable by you alone; point `KNOWLEDGE_MCP_STATE_DIR` at a folder outside every knowledge base. `kbp_explore` writes its Explorer into the same folder.

Each edit your agent records with `kb_record_edit` adds one line to `edits.jsonl` in the same state folder. Each line holds an id, the time, the location text, the ground for the edit (a request in the session, a standing line you wrote, or a change row you accepted) with its quoted text and where a line sits, the text before the edit, the text after the edit or a SHA-256 digest of that text, and the digests of both texts. The text before the edit is a copy of your document's content, kept so the edit can be undone. knowledge-mcp makes no edit itself: your agent edits with its own tools, and the record holds what the agent sends. `kb_edits` returns a location's records, and the log keeps each of those answers too.

To bring in an outside document, your agent sends `kb_mark` the document's text and the location text where the document lives. knowledge-mcp opens nothing at that location, keeps the text only for the call, and keeps each scope's element questions in memory for the session. The log holds a SHA-256 digest of the arguments, the text included, and the answer, which repeats the opening words of each passage. An outside document can carry instructions aimed at your agent; the `km-bring-in` skill has the agent treat every passage as content, mark such a line as a passage, and file nothing without your yes or a line you wrote.

The fit record, `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, lives in your knowledge base, in knowledge-mcp's plugin folder inside the top folder's `.knowledge-bus/`. Your agent writes the file with its own tools; knowledge-mcp writes no file there. `kb_fit_record` reads the record text and the file listing your agent sends, and returns the merged text. For each file, the record holds its path from the knowledge base's top folder, its universe spec id and version and document type id, or "no fit", who the document is for, whether your agent fitted the file or you corrected the fit, the quoted request or standing line that allowed the save and where that line sits, a fingerprint your agent chose, such as a SHA-256 digest of the content, and the time. The record holds no document text, but its paths and quoted lines travel with the knowledge base: anyone who can read the knowledge base can read the record. The log keeps each `kb_fit_record` answer, the merged record text included.

`kb setup <app>` changes your home folder and nothing else:

| App                    | Settings it adds knowledge-mcp to                                                                                                                                    | Skills folder it links into           |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Claude Code            | `mcpServers` in `~/.claude.json`, through `claude mcp add --scope user` when `claude` is on PATH                                                                     | `~/.claude/skills/`                   |
| Codex                  | `[mcp_servers.knowledge-mcp]` in `~/.codex/config.toml`, with `env_vars` listing `KNOWLEDGE_MCP_STATE_DIR` and `XDG_STATE_HOME`, since Codex clears every other name | `~/.agents/skills/`                   |
| The Claude desktop app | `mcpServers` in `~/Library/Application Support/Claude/claude_desktop_config.json`                                                                                    | none: the app takes skills as uploads |
| Pi                     | `mcpServers` in `~/.pi/agent/mcp.json`, through `pi mcp add` when `pi` is on PATH                                                                                    | `~/.agents/skills/`                   |
| OpenCode               | `mcp` in `~/.config/opencode/opencode.json`                                                                                                                          | `~/.agents/skills/`                   |

`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PI_CODING_AGENT_DIR` and `XDG_CONFIG_HOME` move those places as each app documents. The entry runs `kb mcp` by its full path. Without the app's command line, `kb setup` reads the settings file, adds the one entry as one piece of text and checks the result still parses before replacing the file in one step; before changing an existing file it copies the file into `setup/backups/` in the state folder. It refuses to replace an entry named `knowledge-mcp` that runs something else. Each skill link is a symlink to the installed copy; a skill folder of the same name installed another way stays as it is, with a warning.

`kb setup` writes each change in `setup/state.json` in the state folder. `kb setup --remove <app>` undoes exactly those changes: it removes the entry it added (through the app's command line when setup used that command line), so the settings file reads byte for byte as before when nothing else changed in the file; removes the skill links no other set-up app uses; deletes the backups it took; and removes the folders setup created once they are empty, the state folder included. An entry that was there before setup stays. When the entry setup added through the app's command line is already gone, for example deleted by hand, `--remove` skips the command line and undoes the rest. When the command line fails and the entry is still there, `--remove` removes the skill links, keeps its record of the entry, exits 1 with the command to run, and finishes the removal when you run `--remove` again.

Homebrew installs knowledge-mcp from the source archive attached to its GitHub release, and every Python dependency from the source archive and SHA-256 recorded in `uv.lock`, knowledge-bus from its own release archive. The release workflow runs only for a version tag. It pushes the formula to the tap with a fine-grained token that can read and write the tap's contents and nothing else.

On first start, a Claude Code or Codex plugin builds its environment in `$XDG_CACHE_HOME/knowledge-mcp`, else `~/.cache/knowledge-mcp`: uv downloads the dependencies from PyPI and the pinned knowledge-bus release archive from GitHub, and refuses any file whose hash differs from `runtime/requirements.lock`. Later starts reuse the environment. knowledge-bus's skills come with the plugin and run their own bundled checker.

## Supported Versions

Only the latest version on the `main` branch is supported.

## Reporting a Vulnerability

Report privately through GitHub: open the repository's Security tab and choose Report a vulnerability. Include the affected version, steps to reproduce, and the impact. Do not open a public issue.

## Scope

### In Scope

- The `kb` command, the MCP server and the plugin folder `runtime/`, with both plugin manifests
- The settings entries, skill links and backups `kb setup` writes, and their removal by `kb setup --remove`
- The Homebrew formula the release workflow generates
- The marketplace files at the repository root
- Build, check, and dependency tooling

### Out of Scope

- Claude Code, Codex, the ChatGPT and Claude desktop apps, Pi, OpenCode, Homebrew, and their connectors
- The knowledge-bus package, universe specs, and skills knowledge-mcp carries; report those to knowledge-bus
- Other processes running as you

## Known Limitations

- The log keeps every answer and grows until you delete the file. The edit record does the same.
- The fit record holds what the agent sends. knowledge-mcp checks that each recorded document type exists in the universe specs in scope, and checks neither the file listing against the knowledge base nor whether the ground your agent states for saving is true.
- Two chats that save the fit record within the same moment can still drop one chat's entries: each host reads the file again right before writing, and the read and the write are separate steps.
- `kb_mark` splits the text and lists the element questions; your agent marks the passages and decides where each passage goes. knowledge-mcp checks no mark and stops no edit an agent makes against the skill.
- The edit record holds what the agent sends. knowledge-mcp checks neither the text before an edit against your document nor whether the ground your agent states for the edit is true.
- `kbp_explore` writes an Explorer folder of a few hundred kilobytes for each scope and universe spec it explores, under `explorer/` in the state folder. A later call on the same scope and universe spec replaces the folder for that pair; other folders stay until you delete them from `explorer/`.
- `kb setup --remove` and `brew uninstall` remove everything they installed and keep the log, the edit record and any Explorer folders in the state folder, since they hold your history. When `kb setup --remove` removes the last app kb set up, it prints the value of `KNOWLEDGE_MCP_STATE_DIR`, or "not set", and the state folder's path, and deletes nothing there. Homebrew runs no formula code on uninstall, so the formula's caveats name the variable and the folder it points to.
- Claude Code rewrites `~/.claude.json` as it runs, so `claude mcp remove` changes the file's other bytes as Claude Code always does.
- `osv-scanner.toml` lists ignored advisories, each with a reason and an expiry date.
- CI runs no vulnerability scan. The pre-push and post-merge hooks scan the lockfiles and only warn when OSV is unreachable.
