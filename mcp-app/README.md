# mcp-app

The knowledge-mcp MCP App: the cards Claude draws inline in a conversation, built into one HTML file that the server registers as `ui://knowledge-mcp/app.html`. The design is the storyboard canvas `MVdPWv1RzA`; the tokens and build plan are in [design/mcp-app](../design/mcp-app/).

## Layout

```text
mcp-app/
├── src/
│   ├── component-core/              # shadcn base-vega components, never edited by hand
│   ├── component-elements/          # K01–K13: badge, button, chips, tick box, note and the rest
│   ├── component-patterns/          # P01–P07: card shell, change table, summary and full view
│   ├── cards/                       # One card per tool result schema
│   ├── host/                        # Connection, host theme, display mode, ui/message
│   ├── copy/                        # Every user-facing string
│   └── generated/                   # tokens.auto.css from design/mcp-app/kmtokens.js
├── scripts/                         # Token generator
└── vite.config.ts                   # Single-file build
```

## Commands

| Command                        | Purpose                                           |
| ------------------------------ | ------------------------------------------------- |
| `pnpm --filter mcp-app tokens` | Regenerate `src/generated/tokens.auto.css`        |
| `pnpm --filter mcp-app check`  | Token staleness, lint, types, tests and the build |
| `pnpm --filter mcp-app build`  | Write `dist/index.html`                           |
| `just check_mcp_app`           | The same check, as the repo runs it               |

## Rules

The CE Pattern decides where a file goes: core is vendor code, elements take at most one component source, and patterns combine two or more. Dependencies only flow down. A value comes from a token and a string from `src/copy`. A button only sends `ui/message`.
