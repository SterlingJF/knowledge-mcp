"""MCP Apps extension: the `ui://` resource and the tools that render in it.

Hosts without Apps support ignore the `_meta.ui` keys and keep the text result.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.apps import EXTENSION_ID, Apps, ResourceCsp, client_supports_apps
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext

HTML = Path(__file__).parent / "ui" / "app.html"
# Hosts cache a ui:// resource by its URI, so each build of the view gets its own: a changed
# app.html changes the URI and hosts fetch it again. The bare URI keeps serving the current
# view for tool lists a host cached before.
BARE_URI = "ui://knowledge-mcp/app.html"
URI = (
    f"ui://knowledge-mcp/app-{hashlib.sha256(HTML.read_bytes()).hexdigest()[:12]}.html"
)
# The ext-apps SDK writes both keys so every host finds the app; some read only the flat one.
LEGACY_KEY = "ui/resourceUri"
TOOLS = ("kb_prepare_proposal", "kb_record_edit", "kb_prepare_document_moves")
# Claude serves the host fonts from this origin.
CSP = ResourceCsp(resource_domains=["https://assets.claude.ai"])
# Replaces the markdown card for a client that draws the app, so the card isn't shown twice.
DRAWN = (
    "The person already sees this result as an interactive card, so don't repeat `card` in "
    "your reply. Add only your own lines."
)


async def drawn_card(
    ctx: ServerRequestContext[Any, Any], call_next: CallNext
) -> HandlerResult:
    """For a client that draws the app, swap a card tool's markdown text block for DRAWN.

    Middleware sees the result as its wire dict.

    The tool descriptions ask for `card` to be shown unchanged, which hosts without Apps need.
    """
    result = await call_next(ctx)
    name = (ctx.params or {}).get("name")
    if (
        ctx.method != "tools/call"
        or name not in TOOLS
        or not isinstance(result, dict)
        or result.get("isError")
        or not client_supports_apps(ctx)
    ):
        return result
    card = (result.get("structuredContent") or {}).get("card")
    content = [
        block | {"text": DRAWN}
        if block.get("type") == "text" and block.get("text") == card
        else block
        for block in result.get("content", [])
    ]
    return result | {"content": content}


def register(mcp: MCPServer) -> dict[str, dict[str, Any]]:
    """Bind TOOLS to the app resource; return the capability to advertise."""
    apps = Apps()
    html = HTML.read_text(encoding="utf-8")
    for uri in (URI, BARE_URI):
        apps.add_html_resource(
            uri, html, name="knowledge-mcp", csp=CSP, prefers_border=True
        )
    for binding in apps.resources():
        mcp.add_resource(binding.resource)
    for name in TOOLS:
        tool = mcp.tools.get_tool(name)  # type: ignore[attr-defined]
        if tool is None:
            message = f"Apps tool not registered: {name}"
            raise ValueError(message)
        tool.meta = {**(tool.meta or {}), "ui": {"resourceUri": URI}, LEGACY_KEY: URI}
    mcp.middleware.append(drawn_card)
    return {EXTENSION_ID: apps.settings()}
