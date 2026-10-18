"""Build tool results and log each result before returning it."""

from __future__ import annotations

import contextlib
import json
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from knowledge_mcp import log, problems
from knowledge_mcp.kbp import Printed


def sent(**arguments: Any) -> dict[str, Any]:
    """Drop None arguments and unset model fields, so the logged digest covers only the arguments the agent sent."""
    return {
        name: _plain(value) for name, value in arguments.items() if value is not None
    }


def _plain(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_unset=True)
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def compact(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def answer(
    tool: str,
    location: str,
    arguments: dict[str, Any],
    model: type[BaseModel],
    data: dict[str, Any],
) -> CallToolResult:
    """Validate `data` against `model`, log the result, and return the validated data as
    structured content and as one JSON text block."""
    structured = model.model_validate(data).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    text = compact(structured)
    log.record(tool, location, arguments, [text])
    return CallToolResult(
        content=[TextContent(type="text", text=text)], structured_content=structured
    )


def _streams(output: Printed) -> list[TextContent]:
    return [
        TextContent(type="text", text=text, meta={"stream": stream})
        for stream, text in (("stdout", output.stdout), ("stderr", output.stderr))
        if text
    ]


def error(
    tool: str, location: str, arguments: dict[str, Any], failure: problems.Error
) -> CallToolResult:
    """Log the error text if possible, then return the problem object as structured content and its detail as text.

    When kbp fails, kbp's stdout and stderr blocks come first, as in a `kbp_*` result.
    """
    blocks: list[TextContent] = []
    meta = None
    if isinstance(failure, problems.KbpFailed):
        blocks += _streams(failure.output)
        meta = {"exit_code": failure.output.code}
    blocks.append(TextContent(type="text", text=failure.detail))
    # A failed log write must not replace the problem being returned.
    with contextlib.suppress(OSError):
        log.record(tool, location, arguments, [block.text for block in blocks])
    return CallToolResult(
        content=list(blocks),
        structured_content=failure.details(),
        is_error=True,
        meta=meta,
    )


def printed(
    tool: str,
    location: str,
    arguments: dict[str, Any],
    output: Printed,
    note: dict[str, Any] | None = None,
) -> CallToolResult:
    """Log the result, then return kbp's stdout and stderr unchanged.

    Append `note` as a JSON text block with `meta.stream` set to `knowledge-mcp`.

    `is_error` is true when kbp exits with a nonzero code.
    """
    blocks = _streams(output)
    if note:
        blocks.append(
            TextContent(
                type="text", text=compact(note), meta={"stream": "knowledge-mcp"}
            )
        )
    log.record(tool, location, arguments, [block.text for block in blocks])
    return CallToolResult(
        content=list(blocks), is_error=output.code != 0, meta={"exit_code": output.code}
    )
