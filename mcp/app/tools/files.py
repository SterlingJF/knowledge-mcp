from __future__ import annotations

from typing import Any
from urllib.parse import quote

from mcp.types import ToolAnnotations

from app import km_api


def register(mcp: Any) -> None:
    @mcp.tool(
        name='km_list_files',
        description=(
            'List every file in the vault content folders. Each result includes a vault-relative '
            'path and an absolute local path for direct retrieval.'
        ),
        annotations=ToolAnnotations(
            title='List vault files',
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def list_files(vault: str | None = None) -> dict[str, Any]:
        payload, receipt = km_api.request('GET', '/files', vault=vault)
        return {
            'count': len(payload or []),
            'files': payload,
            '_request': receipt,
        }

    @mcp.tool(
        name='km_read_file',
        description=(
            'Read one vault file by its vault-relative path. Markdown content is returned inline; '
            'other file types return their absolute local path for direct retrieval.'
        ),
        annotations=ToolAnnotations(
            title='Read a vault file',
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def read_file(path: str, vault: str | None = None) -> dict[str, Any]:
        payload, receipt = km_api.request(
            'GET', f'/files/{quote(path, safe="/")}', vault=vault
        )
        return {'file': payload, '_request': receipt}
