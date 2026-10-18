from __future__ import annotations

from typing import Any

REINSTALL = "Reinstall with brew reinstall knowledge-mcp."
REPORT = (
    "Run kb doctor --verbose and report the output at "
    "https://github.com/SterlingJF/knowledge-mcp/issues."
)


class KbError(RuntimeError):
    """`fix` is the next step kb prints after the message. With no fix, kb prints REPORT."""

    exit_code = 1

    def __init__(self, message: str, fix: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix


class InstallFault(KbError):
    """A file or package in the kb install is missing or damaged."""

    def __init__(self, message: str) -> None:
        super().__init__(message, REINSTALL)


class UsageFault(KbError):
    """A path or value on the command line is invalid."""

    exit_code = 2


class ToolFault(KbError):
    """kb type failed in kb_get_document_type or on an invalid document-types file.

    `problem` holds the RFC 9457 problem object that kb prints with --json.
    """

    def __init__(self, problem: dict[str, Any], fix: str) -> None:
        super().__init__(problem["detail"], fix)
        self.problem = problem
