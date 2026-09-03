# File: mcp/app/tools/vaults.py

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations

from app import km_api


def register(mcp: Any) -> None:
    @mcp.tool(
        name='km_list_vaults',
        description=(
            'List the vaults the engine serves: id, name, path. Pass a vault id as the '
            '`vault` argument of the artifact tools to target one; omit it for the default '
            'vault.'
        ),
        annotations=ToolAnnotations(
            title='List vaults',
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def list_vaults() -> dict[str, Any]:
        payload, receipt = km_api.request('GET', '/vaults')
        return {
            'count': len(payload or []),
            'vaults': payload,
            '_request': receipt,
        }
