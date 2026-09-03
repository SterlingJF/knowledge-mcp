<h1 align="center">Knowledge-MCP</h1>

<p align="center">
  <strong>Opinionated MCP/API for your notes.</strong><br/>
  Pick a folder, connect your agents, and keep your notes organized.<br/>
  It's free, extensible, and works completely offline.
</p>

Inspired by @nickmilo's [ACE folder system](https://forum.obsidian.md/t/the-ultimate-folder-system-a-quixotic-journey-to-ace/63483), Knowledge-MCP runs in the background and serves the folders you choose locally without sending data to the cloud.

The goal is to keep knowledge clear and organized for agents and humans.

- **Clear** — minimizes agent context and human effort when retrieving or classifying knowledge.
- **Organized** — follows a repeatable structure that agents and humans can recognize.

## Install

[Download the latest release](https://github.com/SterlingJF/knowledge-mcp/releases/latest).

## Quick start

1. **Launch** Knowledge-MCP.
2. **Add** a folder (or create a fresh vault).
3. **Register** the endpoint using one of the client configurations below.

## Connect a client

The service listens at `http://127.0.0.1:17952/mcp`.

Client-specific setup:

### Claude Code

```bash
claude mcp add --transport http knowledge-mcp http://127.0.0.1:17952/mcp
```

### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{ "mcpServers": { "knowledge-mcp": { "url": "http://127.0.0.1:17952/mcp" } } }
```

### Claude Desktop

Claude Desktop's connectors dial from Anthropic's cloud, which cannot reach `127.0.0.1`, and its
local config is stdio-only — bridge with [mcp-remote](https://github.com/geelen/mcp-remote)
(community tool) in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{ "mcpServers": { "knowledge-mcp": { "command": "npx", "args": ["-y", "mcp-remote", "http://127.0.0.1:17952/mcp"] } } }
```

### Other clients

| Client | Config file | Entry |
| --- | --- | --- |
| Codex | `~/.codex/config.toml` | `[mcp_servers.knowledge-mcp]` then `url = "http://127.0.0.1:17952/mcp"` — recent Codex; older builds need the mcp-remote bridge |
| OpenCode | `opencode.json` | `"knowledge-mcp": { "type": "remote", "url": "http://127.0.0.1:17952/mcp", "enabled": true }` under `"mcp"` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `"knowledge-mcp": { "serverUrl": "http://127.0.0.1:17952/mcp" }` |
| Zed | `settings.json` | `"context_servers": { "knowledge-mcp": { "url": "http://127.0.0.1:17952/mcp" } }` |
| Gemini CLI | `~/.gemini/settings.json` | `"knowledge-mcp": { "httpUrl": "http://127.0.0.1:17952/mcp" }` — the field is `httpUrl` |

## How it works

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

- The MCP serves protocol revision (2026-07-28). Does not support earlier revisions.
- Serving is all-or-nothing from the tray; there is no per-vault or MCP-only toggle yet.
- Knowledge models are selected globally at startup; automatic discovery and live per-vault
  loading of knowledge-bus `<folder>-spec/` outputs has not shipped yet.

## Docs

See [docs](./docs/)

## Roadmap

- Vault upkeep automation — scheduled hygiene the service performs for a watched vault.
- Scoped reads and a query surface.
- Configurable folder mapping for existing vault conventions.
- Dynamic knowledge-model discovery — load global and per-vault knowledge-bus `<folder>-spec/`
  outputs as they appear.
- Linux and Windows launchers.
- Per-vault serving controls and an MCP-only toggle.

## Related Projects

- [knowledge-bus](https://github.com/SterlingJF/knowledge-bus) - The knowledge schema used. knowledge-bus structures your knowledge; knowledge-mcp structures your vault and serves it to agents.

## Credits

- Folder shape inspired by Nick Milo's ACE framework (Atlas / Calendar / Efforts) —
  [the forum post](https://forum.obsidian.md/t/the-ultimate-folder-system-a-quixotic-journey-to-ace/63483).
- The plain-files-for-agents stance follows Andrej Karpathy's
  [append-and-review note](https://karpathy.bearblog.dev/the-append-and-review-note/) (2025) and
  [LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (2026).

## Contributing

Issues welcome; PRs by discussion first.

## License

MIT License — see [LICENSE](LICENSE).

The code is open source; the Knowledge-MCP name and branding are not. Forks should use their own identity and not imply affiliation.
