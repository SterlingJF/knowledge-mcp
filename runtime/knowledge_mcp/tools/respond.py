"""Tool answers: logged once, then returned."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from knowledge_mcp import log
from knowledge_mcp.kbp import Printed


def sent(**arguments: Any) -> dict[str, Any]:
    """The arguments as the host sent them: unset fields and absent options left out."""
    return {
        name: _plain(value) for name, value in arguments.items() if value is not None
    }


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_unset=True)
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def compact(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def answer(
    tool: str,
    location: str,
    arguments: dict[str, Any],
    blocks: list[TextContent],
    *,
    is_error: bool = False,
    meta: dict[str, Any] | None = None,
) -> CallToolResult:
    log.record(tool, location, arguments, [block.text for block in blocks])
    return CallToolResult(content=blocks, is_error=is_error, meta=meta)


def refusal(
    tool: str, location: str, arguments: dict[str, Any], message: str
) -> CallToolResult:
    return answer(
        tool,
        location,
        arguments,
        [TextContent(type="text", text=message)],
        is_error=True,
    )


def printed(
    tool: str,
    location: str,
    arguments: dict[str, Any],
    output: Printed,
    note: dict[str, Any] | None = None,
) -> CallToolResult:
    """kbp's stdout and stderr as is, each in its own block, then knowledge-mcp's note."""
    blocks = [
        TextContent(type="text", text=text, meta={"stream": stream})
        for stream, text in (("stdout", output.stdout), ("stderr", output.stderr))
        if text
    ]
    if note:
        blocks.append(
            TextContent(
                type="text", text=compact(note), meta={"stream": "knowledge-mcp"}
            )
        )
    return answer(
        tool,
        location,
        arguments,
        blocks,
        is_error=output.code != 0,
        meta={"exit_code": output.code},
    )
