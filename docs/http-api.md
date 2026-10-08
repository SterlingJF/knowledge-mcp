# HTTP API

The engine listens on `http://127.0.0.1:17951` — loopback only. The MCP server is one of its clients.

The loopback API is a trusted-local interface, not an authentication boundary: any process running
as you can act as you.

## Surface

| Path                                                                                                        | What                                                                                                |
| ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `GET/POST /api/v1/artifacts`, `GET/PUT/DELETE /api/v1/artifacts/{id}`, `POST /api/v1/artifacts/{id}/status` | Artifacts over the file store.                                                                      |
| `GET /api/v1/files`, `GET /api/v1/files/{path}`                                                             | Every file under the five content folders. Markdown is inline; other files return their local path. |
| `GET /api/v1/universes`, `/{id}`, `/{id}/guidance`                                                          | The bundled knowledge models, read-only.                                                            |
| `GET/POST /api/v1/vaults`, `POST /api/v1/vaults/open`, `GET/PATCH/DELETE /api/v1/vaults/{vaultId}`          | Vault lifecycle, typed against [the contract](../contracts/project/v1/vault.rest.openapi.yaml).     |
| `GET /health`, `GET /ready`                                                                                 | Liveness and readiness.                                                                             |

## Headers

- `X-Km-Vault: <id>` — which vault answers this request. Absent, the engine's default vault.
  Unknown ids are refused, not defaulted.
- `X-Km-Agent: <slug>` — declares the caller an agent; writes are recorded as `agent:<slug>` and
  commits are refused. Absent or invalid, the caller is the local person.
- `X-Km-Client: <name>` — logged, nothing more.
- `ETag` — returned on single-artifact reads and writes, computed from file bytes at response time.
- `If-Match` — required on artifact PUT. An absent value returns 428; a value invalidated by an
  intervening edit returns 409.

## Configuration

One resolution order on every surface: command-line flag, then `KM_*` environment, then
`~/.config/knowledge-mcp/config.json`, then the default. The config file is written atomically
and never raises — a malformed file means "no store configured," logged, not crashed.

| Variable                 | What it sets                                                                                                                                                             |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `KM_STORE_ROOT`          | The default vault's folder. Overrides the config file's most recent vault.                                                                                               |
| `KM_PRINCIPAL_ID`        | Who local writes are recorded as. Defaults to the OS username.                                                                                                           |
| `KM_KNOWLEDGE_MODEL_DIR` | Where the knowledge models load from. Unset, the frozen `km-server` uses the set it bundles. Run from source, the engine needs this variable or `--knowledge-model-dir`. |
| `KM_MCP_PORT`            | The MCP server's port. Default 17952.                                                                                                                                    |
| `KM_MCP_API_ORIGIN`      | The engine origin the MCP server calls. Default `http://127.0.0.1:17951/api/v1`.                                                                                         |
