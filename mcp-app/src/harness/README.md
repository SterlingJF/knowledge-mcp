# Local host harness

A dev page that hosts the built app the way Claude does: the bytes of `dist/index.html` (served as `ui://knowledge-mcp/app.html`) in a sandboxed iframe (`allow-scripts allow-same-origin`, transparent), talking over an ext-apps `AppBridge`.

## Run

1. `pnpm --filter mcp-app build`
2. `pnpm --filter mcp-app dev`, then open `/harness.html`.

Rebuild after changing app source; the harness loads `dist/`, not the source.

- **Theme** toggles light and dark, with Claude's style variables read from `design/mcp-app/kmtokens.js`.
- **Width** toggles a 760px and a 360px container.
- **Send a younger result** adds a second iframe with a later result for the same document; the first card should stand down.
- The log lists, in order, every context and result the host sent and every `ui/message`, `ui/update-model-context`, `ui/request-display-mode` and size change it received. A fullscreen request resizes the iframe to 1100 × 720.

## Results

`proposal.result.json` and `proposal.younger.result.json` are real `kb_prepare_proposal` answers (E02 data with a `document_digest`). Regenerate them from the repo root:

`uv run --project runtime python mcp-app/src/harness/capture-proposal.py`

`host.test.ts` drives the host wiring against a real `App` without a browser; what needs the browser (iframe sizing, the card drawing) is checked by hand here.
