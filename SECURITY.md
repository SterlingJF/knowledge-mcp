# Security Policy

## Trust Model

Knowledge-MCP runs on your Mac and serves the folders you choose to agents on the same machine. It makes no outbound network calls.

The engine's HTTP API listens on `127.0.0.1:17951` and the MCP server on `127.0.0.1:17952`; both are loopback only. The HTTP API trusts every local caller: any process running as you can act as you. Its CORS policy admits only the desktop window's origins. The MCP server rejects requests whose `Host` or `Origin` header names anything but a loopback address.

Agents reach your folders through the MCP server. It declares itself an agent on every request. The engine records an agent's writes in the agent's name and refuses:

- a path outside the declared folders, or outside the vault;
- a file that already exists;
- an update without the file's current ETag;
- a record asserted in a person's name;
- a commit; only a person commits.

[How writes are refused](./docs/how-writes-are-refused.md) describes each refusal. The engine performs every file operation. The desktop window has no shell or file-system permission. Its content security policy allows only the engine's loopback port.

Release builds are signed with a Developer ID certificate, run with the hardened runtime, and are notarized by Apple. The release script staples the notarization ticket and verifies the signature and the ticket.

## Supported Versions

Only the [latest release](https://github.com/SterlingJF/knowledge-mcp/releases/latest) is supported.

## Reporting a Vulnerability

Report privately through GitHub: open the repository's Security tab and choose Report a vulnerability. Include the affected version, steps to reproduce, and the impact. Do not open a public issue.

## Scope

### In Scope

- The macOS app: the launcher, the engine, and the MCP server
- The HTTP API and the MCP endpoint
- The agent plugin manifest in `mcp-server/plugin/`
- Build, release, and dependency tooling

### Out of Scope

- MCP clients, and bridges such as mcp-remote
- The knowledge-bus specifications the engine loads
- Other processes running as you
- macOS and its webview

## Known Limitations

- An HTTP API request without `X-Km-Agent` acts as you: it can write in your name and commit.
- The app's entitlements allow unsigned executable memory and disable library validation. The bundled engine and MCP server need both to load their libraries.
- `osv-scanner.toml` lists ignored advisories, each with a reason and an expiry date.
- CI runs no vulnerability scan. The pre-push and post-merge hooks scan the lockfiles and only warn when OSV is unreachable.
