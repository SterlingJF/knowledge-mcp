# knowledge-mcp

Plain, structured thinking while you work. It's free, open, and local-first.

## Example

You ask your agent: "Draft a proposal to move our team to a new tool. We need approval. Moving back will be costly."

![Before drafting, the agent identifies the reviewer, asks about imposed limits and work order, and consults problem and risk notes. Approval and costly reversal make those questions required.](docs/assets/knowledge-mcp-flow.svg)

## Features

- **Document context.** Give your agent each file's document type, reader and questions, in any folder, drive or page your agent can reach.
- **Proposed names and folders.** Get a proposed name and folder for each file with a document type, and accept one file or a whole folder at a time.
- **Naming and filing conventions.** Set naming and filing conventions per document type, from your current folders, a template such as ACE or PARA, or from scratch.
- **Structure by folder.** Set one or more universe specs for your whole knowledge base or for any single folder.
- **Team folders.** Keep each team's terms, document types and conventions in the team's folder, and see which conventions each folder uses.
- **Guided writing.** See each section's questions as you write, and leave each condition open until you confirm its value.
- **Writing for the reader.** Get drafts written for each document type's reader, once you confirm your role.
- **Knowledge import.** Turn notes and conversations into proposed updates to your documents.
- **Conflicting answers.** Keep both versions side by side when new material contradicts a note, and choose which version stays.
- **Folder review.** Find stale items, open questions and contradictions in any folder you import, without changing your originals.
- **Document memory.** Keep each file's document type, reader and your corrections across sessions and parallel chats.
- **File changes.** See new, moved and deleted files at the start of each session, plus the files that still need a document type.
- **Edit history.** Compare original and revised text, and undo recorded edits.
- **Starters.** Start with ready-made document types for product development or codebase recordkeeping in any folder without a universe spec.
- **Custom document types.** Add or change document types with the included knowledge-bus skills, and see the evidence behind each proposed change.
- **Decision records.** Record each decision with the condition for revisiting the decision.
- **Universe spec explorer.** Browse the sections and questions of any document type, and validate your universe specs.
- **Local-first.** Run knowledge-mcp on your machine with no network calls. Your agent makes every change to your files.
- **Answer log.** Review every answer knowledge-mcp gives in a log kept outside your knowledge base.

## Get started

On macOS, install the MCP server and the kb CLI with [Homebrew](https://brew.sh/):

```sh
brew install sterlingjf/tap/knowledge-mcp
```

Then register knowledge-mcp with each harness you use:

| Harness           | Command                   |
| ----------------- | ------------------------- |
| Claude Code (CLI) | `kb setup claude-code`    |
| Claude (desktop)  | `kb setup claude-desktop` |
| Codex             | `kb setup codex`          |
| Pi                | `kb setup pi`             |
| OpenCode          | `kb setup opencode`       |

Start a new session afterward. For the Claude desktop app, also run the ZIP command that `kb setup claude-desktop` prints and upload each ZIP through Customize → Skills in Claude. Then ask your agent for a document, as in the example above.

### Plugin alternatives

Claude Code and Codex also offer plugin installation. Plugins need [uv](https://docs.astral.sh/uv/), which downloads Python 3.14 when needed. Use one installation route per harness.

Claude Code:

```text
/plugin marketplace add SterlingJF/knowledge-mcp
/plugin install knowledge-mcp@knowledge-mcp
```

Codex:

```sh
codex plugin marketplace add SterlingJF/knowledge-mcp
codex plugin add knowledge-mcp@knowledge-mcp
```

Start a new session after installation.

### Shell completion

For zsh, add to `~/.zshrc`:

```sh
eval "$(_KB_COMPLETE=zsh_source kb)"
```

For Bash 4.4 or later, add to `~/.bashrc`:

```sh
eval "$(_KB_COMPLETE=bash_source kb)"
```

For Fish, add `env _KB_COMPLETE=fish_source kb | source` to your shell configuration.

## Guides and reference

- [MCP tools](docs/mcp-tools.md).
- [Access and data handling](SECURITY.md).
- [Release checks for maintainers](docs/release-check.md).
- [Contributing](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).

The code is open source; the knowledge-mcp name and branding are not. Forks need their own name and branding, with no claim of affiliation.
