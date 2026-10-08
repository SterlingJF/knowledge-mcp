# File: mcp-server/app/front_door.py
"""ASGI revision gate for `MCP_REVISION`. Request-body replay for version in `params._meta`."""

from __future__ import annotations

import json
from typing import Any

from app.settings import (
    MCP_REVISION,
    META_CLIENT_CAPABILITIES_KEY,
    META_CLIENT_INFO_KEY,
    META_PROTOCOL_VERSION_KEY,
)

INVALID_REQUEST = -32600

_HTTP_BAD_REQUEST = 400
_HTTP_METHOD_NOT_ALLOWED = 405


class FrontDoor:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")

        if method != "POST":
            _log(
                method,
                None,
                f"refused {_HTTP_METHOD_NOT_ALLOWED} (only POST is served)",
            )
            await _refuse(
                send,
                status=_HTTP_METHOD_NOT_ALLOWED,
                request_id=None,
                message=(
                    f"This server serves MCP {MCP_REVISION} over Streamable HTTP: POST only. "
                    f"The removed GET stream and the HTTP+SSE transport are not implemented."
                ),
                extra_headers=[(b"allow", b"POST")],
            )
            return

        body = await _read_body(receive)
        seen = _inspect(scope, body)

        if seen["headerVersion"] != MCP_REVISION or seen["metaVersion"] != MCP_REVISION:
            _log(method, seen, f"refused {_HTTP_BAD_REQUEST} (not {MCP_REVISION})")
            await _refuse(
                send,
                status=_HTTP_BAD_REQUEST,
                request_id=seen["id"],
                message=(
                    f"This server serves MCP {MCP_REVISION} only. Send the header "
                    f"MCP-Protocol-Version: {MCP_REVISION} and set "
                    f'params._meta["{META_PROTOCOL_VERSION_KEY}"] to the same value. '
                    f"The pre-2026 initialize handshake is not served. In Claude Code, start the "
                    f"host with MCP_SDK_GENERATION=v2 and MCP_PROTOCOL_NEGOTIATION=auto."
                ),
            )
            return

        _log(method, seen, "served")
        await self.app(scope, _replay(body, receive), send)


async def _read_body(receive: Any) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(chunks)


def _replay(body: bytes, original: Any) -> Any:
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if delivered:
            return await original()
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _inspect(scope: dict[str, Any], body: bytes) -> dict[str, Any]:
    headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }

    seen: dict[str, Any] = {
        "headerVersion": headers.get("mcp-protocol-version"),
        "headerMethod": headers.get("mcp-method"),
        "name": headers.get("mcp-name"),
        "metaVersion": None,
        "capabilities": None,
        "client": None,
        "method": None,
        "id": None,
    }

    try:
        payload = json.loads(body)
    except ValueError, TypeError:
        return seen

    if not isinstance(payload, dict):
        return seen

    seen["method"] = payload.get("method")
    seen["id"] = payload.get("id")

    meta = payload.get("params", {})
    meta = meta.get("_meta", {}) if isinstance(meta, dict) else {}
    if not isinstance(meta, dict):
        return seen

    seen["metaVersion"] = meta.get(META_PROTOCOL_VERSION_KEY)

    capabilities = meta.get(META_CLIENT_CAPABILITIES_KEY)
    if isinstance(capabilities, dict):
        seen["capabilities"] = ",".join(sorted(capabilities)) or None

    info = meta.get(META_CLIENT_INFO_KEY)
    if isinstance(info, dict):
        seen["client"] = f"{info.get('name', '?')}/{info.get('version', '?')}"

    return seen


async def _refuse(
    send: Any,
    *,
    status: int,
    request_id: Any,
    message: str,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": INVALID_REQUEST, "message": message},
        }
    ).encode()

    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"mcp-protocol-version", MCP_REVISION.encode()),
                *(extra_headers or []),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


def _log(method: str, seen: dict[str, Any] | None, verdict: str) -> None:
    fields = seen or {}
    parts = [
        f"method={method}",
        f"rpc={fields.get('method') or '-'}",
        f"name={fields.get('name') or '-'}",
        f"hdrVersion={fields.get('headerVersion') or '-'}",
        f"metaVersion={fields.get('metaVersion') or '-'}",
        f"caps={fields.get('capabilities') or '-'}",
        f"client={fields.get('client') or '-'}",
    ]
    print(f"[mcp] {' '.join(parts)} -> {verdict}", flush=True)
