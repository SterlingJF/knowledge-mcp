"""Tool errors as RFC 9457 problem details. problem.schema.yaml lists the problem types."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from knowledge_mcp.errors import REINSTALL, REPORT

if TYPE_CHECKING:
    from pydantic import ValidationError

    from knowledge_mcp.kbp import Printed

BASE = "https://github.com/SterlingJF/knowledge-mcp/problems/"


class Error(Exception):
    """`errors` pairs each message with a JSON Pointer to the argument at fault.

    Given `pointer` and no `errors`, add one entry that pairs `detail` with `pointer`.
    """

    code = "internal-error"

    def __init__(
        self,
        detail: str,
        *,
        code: str | None = None,
        pointer: str | None = None,
        errors: Sequence[tuple[str, str]] = (),
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code
        found = list(errors)
        if pointer is not None and not found:
            found.append((detail, pointer))
        self.errors = found

    def details(self) -> dict[str, Any]:
        """The problem object, validated against problem.schema.yaml."""
        from knowledge_mcp import schemas  # noqa: PLC0415
        from knowledge_mcp.models_auto.problem_schema import (  # noqa: PLC0415
            ProblemDetails,
        )

        problem: dict[str, Any] = {
            "type": BASE + self.code,
            "title": schemas.title(self.code),
            "detail": self.detail,
        }
        if self.errors:
            problem["errors"] = [
                {"detail": detail, "pointer": pointer}
                for detail, pointer in self.errors
            ]
        return ProblemDetails.model_validate(problem).model_dump(
            mode="json", exclude_unset=True
        )


class KbpFailed(Error):
    """kbp exited nonzero during a tool call."""

    code = "kbp-failed"

    def __init__(self, output: Printed, mode: str) -> None:
        flag = "" if mode == "validate" else " --" + mode.replace("_", "-")
        super().__init__(f"kbp{flag} exited with code {output.code}.")
        self.output = output


class KbpMissing(RuntimeError): ...


class KbpVersionSkew(Error):
    """kbp printed no JSON object, or printed JSON with an unsupported `schema` value."""

    code = "kbp-version-skew"


def pointer(*parts: str | int) -> str:
    """A JSON Pointer into the tool arguments, such as `#/entries/0/document_type`."""
    escaped = (str(part).replace("~", "~0").replace("/", "~1") for part in parts)
    return "#" + "".join("/" + part for part in escaped)


def _listed(names: Sequence[str]) -> str:
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def unknown_arguments(tool: str, names: Sequence[str], known: Sequence[str]) -> Error:
    taken = f"Its arguments are {_listed(known)}" if known else "It takes no arguments"
    noun = "argument" if len(names) == 1 else "arguments"
    detail = f"{tool} takes no {noun} named {_listed(names)}. {taken}."
    return Error(
        detail,
        code="argument-invalid",
        errors=[
            (f"{tool} takes no argument named {name}.", pointer(name)) for name in names
        ],
    )


def _invalid_arguments(tool: str, error: ValidationError) -> Error:
    """Pydantic's argument errors as one problem, without input values or documentation links."""
    found = []
    for item in error.errors(include_url=False, include_input=False):
        place = pointer(*item["loc"])
        found.append((f"{place[2:] or tool}: {item['msg']}", place))
    detail = f"Invalid arguments for {tool}. " + " ".join(
        f"{message}." for message, _ in found
    )
    code = (
        "conventions-invalid"
        if tool == "kb_prepare_conventions"
        and any(place.startswith("#/changes/") for _, place in found)
        else "argument-invalid"
    )
    return Error(detail, code=code, errors=found)


def from_exception(error: BaseException, tool: str) -> Error:
    """Unwrap the MCP SDK's ToolError first. Map an unknown exception to internal-error."""
    from mcp.server.mcpserver.exceptions import ToolError  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    if isinstance(error, ToolError) and error.__cause__ is not None:
        error = error.__cause__
    if isinstance(error, Error):
        return error
    if isinstance(error, ValidationError) and error.title.endswith("Arguments"):
        return _invalid_arguments(tool, error)
    if isinstance(error, KbpMissing):
        return Error(f"{error} {REINSTALL}", code="kbp-failed")
    message = str(error).rstrip(".") or type(error).__name__
    return Error(f"knowledge-mcp failed: {message}. {REPORT}")
