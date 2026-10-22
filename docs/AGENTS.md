# knowledge-mcp docs

Mintlify site for knowledge-mcp. Pages are MDX with YAML frontmatter; navigation, colors and links live in `docs.json`.

## Terminology

- knowledge-mcp is a toolkit your AI assistant uses. Never call it an assistant.
- Say "your assistant" for the AI doing the work, and name apps (Claude Code, Codex, Claude Desktop, Pi, OpenCode) rather than one harness.
- Use "knowledge base" for the user's folder and `.knowledge-bus` only where the folder path matters.

## Writing rules

- Keep the owner-reviewed wording. Change format, links and components, not prose, unless asked.
- No filler, marketing, vague pronouns or caveats nobody asked for. A revision must not make a section longer.
- Setup ends at `kb setup` or plugin installation. No uploads, restarts or confirmation steps; `kb doctor` belongs in troubleshooting only.
- Support goes to GitHub Issues; vulnerabilities go to the private security advisory.
- Page descriptions: 130 to 160 characters, plain and specific.

## Checks

Run `pnpm dlx mint validate` and `pnpm dlx mint broken-links` from this folder.
