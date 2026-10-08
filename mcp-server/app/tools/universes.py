# File: mcp-server/app/tools/universes.py

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from app import km_api


def register(mcp: Any) -> None:
    @mcp.tool(
        name="km_list_universes",
        description=(
            "List the universes this build carries. Start here: an artifact names a universe "
            "and a version, and every code in its data is resolved against that universe."
        ),
        annotations=ToolAnnotations(
            title="List universes",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def list_universes() -> dict[str, Any]:
        payload, receipt = km_api.request("GET", "/universes")
        return {
            "count": len(payload or []),
            "universes": payload,
            "_request": receipt,
        }

    @mcp.tool(
        name="km_read_universe",
        description=(
            "Read one universe in full: its elements, artifact types and their compositions, "
            "frames, factors and relations. This is what says which element codes an artifact "
            "type is made of and which statuses an instance record may carry. Codes are opaque "
            "handles — resolve them here for your own reading, and never show a code to a "
            "person."
        ),
        annotations=ToolAnnotations(
            title="Read a universe",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def read_universe(universe_id: str) -> dict[str, Any]:
        payload, receipt = km_api.request("GET", f"/universes/{universe_id}")
        return {"universe": payload, "_request": receipt}

    @mcp.tool(
        name="km_read_universe_guidance",
        description=(
            "Read a universe's guidance: how to answer each element and artifact type well, and "
            "what each value means. Guidance is advisory — diverging from it is not an error. "
            "A universe may have none, in which case this returns nothing found."
        ),
        annotations=ToolAnnotations(
            title="Read universe guidance",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def read_universe_guidance(universe_id: str) -> dict[str, Any]:
        payload, receipt = km_api.request("GET", f"/universes/{universe_id}/guidance")
        return {"guidance": payload, "_request": receipt}
