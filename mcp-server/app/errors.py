# File: mcp-server/app/errors.py

from __future__ import annotations

from typing import Any

# Advice per known backend error code. Unknown codes use generic advice.
_ADVICE: dict[str, str] = {
    "FORBIDDEN": (
        "This is refused, not failed. Do not retry it. Tell the person what you were trying to "
        "do and let them do it."
    ),
    "NOT_FOUND": (
        "Nothing is stored under that id. List the artifacts and use an id from the result "
        "rather than constructing one."
    ),
    "CONFLICT": (
        "The file changed between the read and the write. Read the artifact again, re-apply the "
        "change on top of what is there now, and write once. Do not repeat the original write."
    ),
    "STORE_UNAVAILABLE": (
        "No storage folder is set, so there is nowhere to read or write. Only the person can "
        "choose one, in the desktop app. Stop and tell them."
    ),
    "ELEMENT_CODE_UNRESOLVED": (
        "An element code in `data` is not declared by the universe this artifact names. Read the "
        "universe and use a code from it."
    ),
    "INSTANCE_STATUS_UNDECLARED": (
        "An instance's `status` is not one the universe declares. Read the universe's `statuses` "
        "and use one of those."
    ),
    "DUPLICATE_UNSUPERSEDED_INSTANCE": (
        "Two live instances of one element assert the same thing in the same name. Either "
        "supersede the earlier one or send only the record you mean."
    ),
    "SUPERSEDES_UNRESOLVED": (
        "`supersedes` names a record that is not in the list being written. A correction sends "
        "both records: the one being superseded, carrying its own `id`, and the one superseding "
        "it."
    ),
    "UNIVERSE_UNKNOWN": (
        "This build carries no universe with that id. List the universes and name one of them."
    ),
    "EXHAUSTIVE_ON_UNCLOSABLE_ELEMENT": (
        "This element cannot be claimed exhaustive, because the universe says its answers are "
        "never closed. Leave `exhaustive` unset."
    ),
    "UNPROCESSABLE_ENTITY": (
        "The store understood the request and declined it. Read the message; the payload needs "
        "changing, not resending."
    ),
}

_SCHEMA_ADVICE = (
    "The payload did not match the contract, so nothing was sent to the store. Fix the fields "
    "named above and send it once more. Note that top-level fields are camelCase and the "
    "instance records inside `data` are snake_case."
)


class KmApiError(Exception):
    """Backend response error or transport failure."""

    def __init__(
        self,
        detail: str,
        *,
        status: int,
        error_code: str | None = None,
        fields: dict[str, Any] | None = None,
        schema_rejection: bool = False,
    ) -> None:
        self.detail = detail
        self.status = status
        self.error_code = error_code
        self.fields = fields or {}
        self.schema_rejection = schema_rejection
        super().__init__(self.message)

    @property
    def advice(self) -> str:
        if self.schema_rejection:
            return _SCHEMA_ADVICE
        if self.error_code and self.error_code in _ADVICE:
            return _ADVICE[self.error_code]
        return (
            "The request was not carried out. Read the message before sending anything else; "
            "repeating the same request will produce the same answer."
        )

    @property
    def message(self) -> str:
        """Full text for tool result."""
        parts = [f"{self.status}"]
        if self.error_code:
            parts.append(self.error_code)
        head = " ".join(parts)
        body = f"{head}: {self.detail}"
        if self.fields:
            named = ", ".join(
                f"{key} = {value!r}" for key, value in self.fields.items()
            )
            body = f"{body} ({named})"
        return f"{body}\n\n{self.advice}"


def parse_error_body(status: int, body: Any) -> KmApiError:
    """Build KmApiError from either error body shape."""
    if isinstance(body, dict):
        detail = body.get("detail")

        if isinstance(detail, list):
            return KmApiError(
                _describe_schema_rejection(detail),
                status=status,
                error_code=None,
                schema_rejection=True,
            )

        if isinstance(detail, str):
            return KmApiError(
                detail,
                status=status,
                error_code=body.get("errorCode"),
                fields=body.get("fields"),
            )

    return KmApiError(
        f"The backend answered {status} with a body this client did not recognise: {body!r}",
        status=status,
    )


def _describe_schema_rejection(entries: list[Any]) -> str:
    """Flatten FastAPI's validation array into readable lines."""
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            lines.append(str(entry))
            continue
        location = entry.get("loc") or []
        where = ".".join(str(part) for part in location) or "(payload)"
        lines.append(f"{where}: {entry.get('msg', 'rejected')}")
    return "The payload does not match the contract.\n" + "\n".join(
        f"  - {line}" for line in lines
    )
