"""Build tool results and log each result before returning it."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Callable
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from knowledge_mcp import log, problems
from knowledge_mcp.kbp import Printed
from knowledge_mcp.models_auto.kbp_output_schema import KbpOutputAnswer


def sent(**arguments: Any) -> dict[str, Any]:
    """Prepare arguments for logging: drop None values and serialize models without unset fields.

    Wrapper-supplied defaults remain in the digest when they are not None.
    """
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
    view: Callable[[dict[str, Any]], str | None] | None = None,
) -> CallToolResult:
    """Validate `data` against `model`, log the result, and return the validated data as
    structured content and as one JSON text block.

    With `view`, its markdown goes in the `card` field and in a text block before the JSON block,
    since some hosts give the model only structured content and others only text.
    A view that returns None adds no card.
    """
    card = view(data) if view is not None else None
    if card is not None:
        data = data | {"card": card}
    structured = model.model_validate(data).model_dump(
        mode="json", by_alias=True, exclude_unset=True
    )
    texts = [compact(structured)]
    if card is not None:
        texts.insert(0, card)
    log.record(tool, location, arguments, texts)
    return CallToolResult(
        content=[TextContent(type="text", text=text) for text in texts],
        structured_content=structured,
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

    Structured content is a validated stream receipt on success, or the existing
    coded problem on failure. Raw text blocks and exit metadata stay unchanged.
    `is_error` is true when kbp exits with a nonzero code.
    """
    blocks = _streams(output)
    if note:
        blocks.append(
            TextContent(
                type="text", text=compact(note), meta={"stream": "knowledge-mcp"}
            )
        )
    if output.code != 0:
        structured = problems.KbpFailed(output, tool.removeprefix("kbp_")).details()
    else:
        data: dict[str, Any] = {
            "schema": "knowledge-mcp/kbp-output/1",
            "stdout": output.stdout,
            "stderr": output.stderr,
            "exit_code": output.code,
        }
        if note:
            data["note"] = note
        structured = KbpOutputAnswer.model_validate(data).model_dump(
            mode="json", by_alias=True, exclude_unset=True
        )
    log.record(tool, location, arguments, [block.text for block in blocks])
    return CallToolResult(
        content=list(blocks),
        structured_content=structured,
        is_error=output.code != 0,
        meta={"exit_code": output.code},
    )
