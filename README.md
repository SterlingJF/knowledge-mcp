# knowledge-mcp

Plain, structured thinking while you work. It's free, open, and local-first.

knowledge-mcp brings the defined questions, conditions and connections from your knowledge base into your work with AI agents. Your agent applies the guidance based on your document and situation as you ask, write or review.

Under the hood, [Knowledge Bus](https://github.com/SterlingJF/knowledge-bus) is used to codify domain knowledge as specs.

## How it works

![Before drafting, the agent identifies the reviewer, asks about imposed limits and work order, and consults problem and risk notes. Approval and costly reversal make those questions required.](docs/assets/knowledge-mcp-flow.svg)

## Features

- **Structured Document context.** You and your agent share each document's purpose, reader and questions.
- **Guided writing.** See each section's questions and catch missing answers while you write.
- **Structure by folder.** Set guidance for your whole knowledge base or for individual folders.
- **Knowledge import.** Turn notes and conversations into proposed updates to your documents.
- **Document memory.** Reuse saved document types and reader choices across sessions.
- **Edit history.** Compare original and revised text, and undo recorded edits.
- **Custom guidance.** Set and refine the questions and requirements for your documents.

## Get started

On macOS, install with [Homebrew](https://brew.sh/):

```sh
brew install sterlingjf/tap/knowledge-mcp
```

Then register it with the apps you use:

| App                                                             | Command                   |
| --------------------------------------------------------------- | ------------------------- |
| Claude Code                                                     | `kb setup claude-code`    |
| Codex, including the ChatGPT desktop app's Codex and Work modes | `kb setup codex`          |
| The Claude desktop app                                          | `kb setup claude-desktop` |
| Pi                                                              | `kb setup pi`             |
| OpenCode                                                        | `kb setup opencode`       |

Start a new session afterward. For the Claude desktop app, also upload the included skills from the folder printed by setup. Open your document or connect its source, then try the proposal request above with your own work.

### Plugin alternatives

Claude Code and Codex also offer plugin installation. Plugins need [uv](https://docs.astral.sh/uv/), which downloads Python 3.14 when needed. Use one installation route per app.

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

## Guides and reference

- [Agent reference](docs/mcp-tools.md).
- [Access and data handling](SECURITY.md).
- [Release checks for maintainers](docs/release-check.md).
- [Contributing](CONTRIBUTING.md).

## License

MIT License — see [LICENSE](LICENSE).

The code is open source; the Knowledge-MCP name and branding are not. Forks should use their own identity and not imply affiliation.
