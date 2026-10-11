"""The edit record: one JSON Lines entry per agent edit, in knowledge-mcp's own state folder.

Each entry names the location text, the request, standing line or accepted change row the agent
acted on, and the text before the edit, so the person can check the edit and undo it. The file
sits beside the log, outside every knowledge base, and knowledge-mcp writes nothing else for an
edit: the agent makes the edit with its own tools.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Literal

from knowledge_mcp import log

SCHEMA = "knowledge-mcp/edit/1"
LISTING = "knowledge-mcp/edits/1"
NAME = "edits.jsonl"

Basis = Literal["request", "line", "change_row"]

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class EditError(ValueError):
    """The edit can't be recorded; the message says what to send instead."""


def record(
    *,
    location: str,
    basis: Basis,
    basis_text: str,
    basis_location: str | None,
    before: str,
    after: str | None,
    after_digest: str | None,
    whole_file: bool = False,
) -> dict[str, Any]:
    """Append one edit and return its entry.

    `after_digest` stands in for `after` only when `before` is the whole file: undo then checks
    the whole file against the digest. A passage needs its `after` text, which undo finds again.
    """
    if after is None and after_digest is None:
        msg = "Send `after`, the text that replaced `before`, or its `after_digest`."
        raise EditError(msg)
    if after_digest is not None and not DIGEST.fullmatch(after_digest):
        msg = (
            f"`after_digest` {after_digest!r} is no digest: send `sha256:` and the 64 lowercase "
            "hex digits of the SHA-256 of `after` as UTF-8."
        )
        raise EditError(msg)
    if after is None and not whole_file:
        msg = (
            "Send `after` for an edit to a passage, so the edit can be found and undone. "
            "`after_digest` alone stands in for `after` only with `whole_file` true, when "
            "`before` is the whole file."
        )
        raise EditError(msg)
    if after is not None:
        computed = log.text_digest(after)
        if after_digest is not None and after_digest != computed:
            msg = (
                f"`after_digest` {after_digest} differs from the digest of `after`, "
                f"{computed}: send one of the two, or both for the same text."
            )
            raise EditError(msg)
        after_digest = computed
    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "time": log.now(),
        "location": location,
        "basis": basis,
        "basis_text": basis_text,
    }
    if basis_location is not None:
        entry["basis_location"] = basis_location
    if whole_file:
        entry["whole_file"] = True
    entry["before"] = before
    entry["before_digest"] = log.text_digest(before)
    if after is not None:
        entry["after"] = after
    entry["after_digest"] = after_digest
    log.append(NAME, entry)
    return entry


def receipt(entry: dict[str, Any]) -> dict[str, Any]:
    """The entry without its texts, which the agent already holds."""
    kept = {
        name: value for name, value in entry.items() if name not in ("before", "after")
    }
    return {"schema": SCHEMA, **kept}


def listing(location: str) -> dict[str, Any]:
    """Every recorded edit at the location text, oldest first."""
    path = log.directory() / NAME
    found = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # A line cut short by a crash mid-write records nothing whole.
                continue
            if isinstance(entry, dict) and entry.get("location") == location:
                found.append(entry)
    return {"schema": LISTING, "location": location, "edits": found}
