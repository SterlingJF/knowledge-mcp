# Runtime

## Layout

```text
runtime/
├── knowledge_mcp/
│   ├── cli.py                       # kb entry point
│   ├── main.py                      # MCP server entry point
│   ├── tools/                       # MCP tool modules
│   ├── models_auto/, schemas_auto/  # Generated models and schema bundles
│   └── ...                          # Setup, settings, validation, imports and file history
├── knowledge-bus/                   # Vendored spec files
├── skills/                          # Six knowledge-bus skills and three knowledge-mcp skills
├── scripts/                         # docs/mcp-tools.mdx region generator
└── tests/                           # Unit and end-to-end tests
```

## Commands

| Command                        | Purpose                                                                                                  |
| ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `uv run --locked kb <command>` | Run kb from this checkout, in `runtime/`                                                                 |
| `just check_runtime`           | Run lint, format, type, dead-code and test checks. Check that generated models and tool docs are current |

## Upgrade knowledge-bus

1. Point the `knowledge-bus` pin in `runtime/pyproject.toml` at the release source archive, `https://github.com/SterlingJF/knowledge-bus/releases/download/<tag>/knowledge_bus-<version>.tar.gz`.
2. From the repo root, run `uv lock`.
3. Check that the knowledge-bus hash in `uv.lock` matches the hash in the release `SHA256SUMS` file. Stop if the hashes differ.
4. Run `just refresh_knowledge_model <tag>`.
