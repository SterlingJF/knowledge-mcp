"""MCP Apps extension: the `ui://` resource and the tools that render in it.

Hosts without Apps support ignore the `_meta.ui` keys and keep the text result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.apps import EXTENSION_ID, Apps, ResourceCsp

URI = "ui://knowledge-mcp/app.html"
HTML = Path(__file__).parent / "ui" / "app.html"
TOOLS = ("kb_prepare_proposal", "kb_record_edit", "kb_prepare_document_moves")
# Claude serves the host fonts from this origin.
CSP = ResourceCsp(resource_domains=["https://assets.claude.ai"])


def register(mcp: MCPServer) -> dict[str, dict[str, Any]]:
    """Bind TOOLS to the app resource; return the capability to advertise."""
    apps = Apps()
    apps.add_html_resource(
        URI,
        HTML.read_text(encoding="utf-8"),
        name="knowledge-mcp",
        csp=CSP,
        prefers_border=True,
    )
    for binding in apps.resources():
        mcp.add_resource(binding.resource)
    for name in TOOLS:
        tool = mcp.tools.get_tool(name)  # type: ignore[attr-defined]
        if tool is None:
            message = f"Apps tool not registered: {name}"
            raise ValueError(message)
        tool.meta = {**(tool.meta or {}), "ui": {"resourceUri": URI}}
    return {EXTENSION_ID: apps.settings()}
