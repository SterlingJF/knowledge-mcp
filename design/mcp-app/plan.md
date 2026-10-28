# MCP App build plan

Builds the cards on the storyboard canvas `MVdPWv1RzA` as a knowledge-mcp MCP App. The cards render in Claude (web, desktop, mobile, Cowork). Every tool keeps its text card for hosts without Apps. The order of cards to build is in [todo.md](todo.md).

## Decisions

- **Stack.** React 19 with shadcn `base-vega` as the read-only core and the CE Pattern layers on top, matching Cardtrail. Styling uses Tailwind 4, and the MCP Apps client is `@modelcontextprotocol/ext-apps` 2.0.3, the newest release past the repo's seven-day age rule. Vite and `vite-plugin-singlefile` bundle everything into one HTML file.
- **One resource.** The server registers one `ui://knowledge-mcp/app.html` resource with `mcp.server.apps` from `mcp` 2.2.0. The app picks the card to draw from `structuredContent.schema`.
- **Tokens.** `design/mcp-app/kmtokens.js` stays the only source. A script generates `mcp-app/src/generated/tokens.auto.css` from it, and a check fails when the generated file is out of date.
- **Buttons.** A press sends `ui/message` and nothing else. The server opens no knowledge-base file.
- **Display.** Inline cards show a summary of at most 5 data points and 2 actions. The full view uses fullscreen (amended recommendation 1).
- **Order.** The proposal card ships first, then the saved result and Undo, then the move plan, then the rest.

## Layers

| Layer       | Folder                           | Holds                                                                                      |
| ----------- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| Core        | `mcp-app/src/component-core`     | shadcn: button, badge, checkbox, toggle-group, skeleton, table. Read-only.                 |
| Elements    | `mcp-app/src/component-elements` | K01–K13 on the Components page                                                             |
| Patterns    | `mcp-app/src/component-patterns` | P01–P07 on the Patterns page                                                               |
| Cards       | `mcp-app/src/cards`              | One per card kind, built from patterns                                                     |
| Host bridge | `mcp-app/src/host`               | Connect, host styles and fonts, display mode, size changes, sending messages, supersession |

## Shared files (coordinator only)

`design/mcp-app/*`, `mcp-app/src/generated/*`, `mcp-app/src/copy/*`, `mcp-app/package.json`, `pnpm-lock.yaml`, `contracts/extensions/mcp/v1/*`, `runtime/knowledge_mcp/main.py`, `justfile`, `.github/workflows/ci.yml`, `CONTRIBUTING.md`.

## Lanes

- `just check` runs the repo's full check.
- `pnpm --filter mcp-app check` runs lint, types, tests and format for the app.
- `pnpm --filter mcp-app build` writes the single HTML file.
- Host checks: Claude Desktop, then Claude web; Claude Code for the text fallback.

## Risks

| Risk                                              | Mitigation                                                                                   |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Claude's MCP Apps behaviour differs from the docs | Card 0.3 ships one card end to end before the element batch merges                           |
| Bundle size inside a tool result path             | Single resource, read once, prefetched; check against the 150,000-character note             |
| Supersession key needs a contract change          | Engine card E3 adds `{createdAt, seq}` to UI tool results before the lifecycle pattern lands |
| Text cards missing for most tools (spec MUST)     | Engine cards E4–E6 add Markdown views, sharing copy with the app                             |
