from __future__ import annotations

import difflib
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any

from knowledge_mcp import log, problems
from knowledge_mcp.document_types import OLD_BASIS, normal_path
from knowledge_mcp.models_auto.common_schema import EditOperation
from knowledge_mcp.models_auto.document_types_schema import AllowedBy
from knowledge_mcp.models_auto.edits_schema import Edit

SCHEMA = "knowledge-mcp/edit/2"
LISTING = "knowledge-mcp/edits/2"
NAME = "edits.jsonl"
CHANGED_LINES = 12

DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class EditError(problems.Error):
    """The harness sent an invalid `after` or `after_digest` to kb_record_edit."""

    code = "argument-invalid"


@dataclass(frozen=True)
class Texts:
    before: str
    after: str | None
    after_digest: str | None
    whole_file: bool = False


def _after_digest(texts: Texts) -> str:
    """Return the digest of `after`, or `after_digest` when `after` is missing.

    Raise EditError when `after` and `after_digest` are both missing, or when a passage edit lacks
    `after`. Also raise EditError when `after_digest` is malformed or differs from the digest of
    `after`.
    """
    after, after_digest = texts.after, texts.after_digest
    if after is None and after_digest is None:
        msg = "Send `after` (the text that replaced `before`) or `after_digest`."
        raise EditError(msg, pointer=problems.pointer("after"))
    if after_digest is not None and not DIGEST.fullmatch(after_digest):
        msg = (
            f"`after_digest` {after_digest!r} is not a digest. Send `sha256:` and 64 "
            "lowercase hex digits: the SHA-256 of `after` encoded as UTF-8."
        )
        raise EditError(msg, pointer=problems.pointer("after_digest"))
    if after is None:
        if not texts.whole_file:
            msg = (
                "Send `after` for a passage edit, so undo can find the passage. "
                "Send `after_digest` without `after` only when `before` is the whole file and "
                "`whole_file` is true."
            )
            raise EditError(msg, pointer=problems.pointer("after"))
        assert after_digest is not None
        return after_digest
    computed = log.text_digest(after)
    if after_digest is not None and after_digest != computed:
        msg = (
            f"`after_digest` {after_digest} differs from {computed}, the digest of `after`. "
            "Send `after`, `after_digest`, or both with matching values."
        )
        raise EditError(msg, pointer=problems.pointer("after_digest"))
    return computed


def record(
    location: str,
    allowed_by: AllowedBy,
    texts: Texts,
    operation: EditOperation | None = None,
) -> dict[str, Any]:
    """Append the edit to `edits.jsonl` and return the new entry."""
    after_digest = _after_digest(texts)
    if operation is not None:
        if not texts.whole_file or operation.index > operation.count:
            message = "Grouped edits require whole-file text and an index within the group count."
            raise EditError(message, pointer="#/operation")
        normal_path(operation.old_path, pointer="#/operation/old_path")
        normal_path(operation.path, pointer="#/operation/path")
    entry: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "time": log.now(),
        "location": location,
        "allowed_by": allowed_by.model_dump(mode="json", exclude_none=True),
    }
    if operation is not None:
        entry["operation"] = operation.model_dump(mode="json")
    if texts.whole_file:
        entry["whole_file"] = True
    entry["before"] = texts.before
    entry["before_digest"] = log.text_digest(texts.before)
    if texts.after is not None:
        entry["after"] = texts.after
    entry["after_digest"] = after_digest
    log.append(NAME, entry)
    return entry


def changes(before: str, after: str) -> dict[str, Any]:
    """Return the removed and added lines in document order, capped at CHANGED_LINES."""
    old, new = before.splitlines(), after.splitlines()
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    lines: list[dict[str, str]] = []
    hunks = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        hunks += 1
        lines += [{"change": "removed", "text": text} for text in old[i1:i2]]
        lines += [{"change": "added", "text": text} for text in new[j1:j2]]
    return {
        "hunks": hunks,
        "lines": lines[:CHANGED_LINES],
        "more": max(0, len(lines) - CHANGED_LINES),
    }


def check_undoes(location: str, undoes: str) -> None:
    """Raise EditError when no valid edit recorded for `location` has the id `undoes`.

    A grouped undo is recorded under the group's root, like the edits it undoes.
    """
    if any(edit["id"] == undoes for edit in listing(location)["edits"]):
        return
    msg = (
        f"No edit recorded for {location!r} has the id {undoes!r}. Call `kb_list_edits` "
        "with the same `location` and send the id of the edit this one undoes, or leave "
        "`undoes` out."
    )
    raise EditError(msg, pointer=problems.pointer("undoes"))


def receipt(entry: dict[str, Any], undoes: str | None = None) -> dict[str, Any]:
    """Return the entry with `schema` and without `before` and `after`, which the agent already has.

    Add `changes`, a capped excerpt of the changed lines, so the receipt stays small.
    """
    kept = {
        name: value for name, value in entry.items() if name not in ("before", "after")
    }
    found: dict[str, Any] = {"schema": SCHEMA, **kept}
    if entry["before"] == "" and entry.get("whole_file"):
        found["created"] = True
    if undoes is not None:
        found["undoes"] = undoes
    if "after" in entry:
        found["changes"] = changes(entry["before"], entry["after"])
    return found


def _current(line: dict[str, Any]) -> dict[str, Any]:
    """Move the `basis`, `basis_text` and `basis_location` fields of a 0.2.1 line into `allowed_by`.

    Return other lines unchanged.
    """
    if "allowed_by" in line or "basis" not in line:
        return line
    basis = line["basis"]
    allowed_by = {"basis": OLD_BASIS.get(basis, basis), "text": line.get("basis_text")}
    if line.get("basis_location") is not None:
        allowed_by["location"] = line["basis_location"]
    found: dict[str, Any] = {}
    for name, value in line.items():
        if name == "basis":
            found["allowed_by"] = allowed_by
        elif name not in ("basis_text", "basis_location"):
            found[name] = value
    return found


def listing(location: str) -> dict[str, Any]:
    """Return the edits recorded for `location`, oldest first.

    Skip lines that are not JSON objects or fail the edit schema.
    """
    path = log.directory() / NAME
    found = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                # A crash mid-write can leave a partial last line.
                continue
            if not isinstance(entry, dict) or entry.get("location") != location:
                continue
            current = _current(entry)
            try:
                Edit.model_validate(current)
            except ValueError:
                # Undo can't use a line that fails the edit schema.
                continue
            found.append(current)
    return {"schema": LISTING, "location": location, "edits": found}
