from __future__ import annotations

import posixpath
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

import yaml
from pydantic import TypeAdapter

from knowledge_mcp import log, problems, schemas
from knowledge_mcp.models_auto.common_schema import FileChange, FileDeleted, FileMoved
from knowledge_mcp.models_auto.document_types_schema import (
    AllowedBy,
    Audience,
    Entry,
    SetBy,
    TypedEntry,
    UntypedEntry,
)

__all__ = ["AllowedBy", "Audience", "Entry", "SetBy"]

SCHEMA = "knowledge-mcp/document-types/1"
UPDATE = "knowledge-mcp/document-types-update/1"
PLACE = ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml"
LABEL = "from the document-types file"

# knowledge-mcp 0.2.1 and earlier wrote `record.yaml` with these names and values.
OLD_PLACE = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"
OLD_SCHEMA = "knowledge-mcp/fit-record/1"
OLD_SET_BY = {"fit": "agent", "correction": "person"}
OLD_BASIS = {"line": "instruction", "change_row": "accepted_change"}

HEADER = """\
# Your agent rewrites this file with text from knowledge-mcp when files change or you correct an entry.
# An entry with `set_by: person` overrides any later entry by the agent.
"""

# Files under any `.knowledge-bus/` folder are configuration, never documents.
CONFIGURATION = ".knowledge-bus"

RECORD = problems.pointer("record")
ENTRY: TypeAdapter[Entry] = TypeAdapter(Entry)


class DocumentTypesError(problems.Error):
    """The harness sent an invalid argument to a document-type tool."""

    code = "argument-invalid"


def _record_error(msg: str) -> DocumentTypesError:
    return DocumentTypesError(msg, code="record-invalid", pointer=RECORD)


def _as_text(value: Any) -> Any:
    """Return a version or time as text when YAML parsed the value as a number or date."""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return value


def entry(**fields: Any) -> Entry:
    return ENTRY.validate_python(fields)


def plain(found: Entry) -> dict[str, Any]:
    return found.model_dump(mode="json", exclude_none=True)


def named(found: Entry) -> tuple[str | None, str | None, bool]:
    if isinstance(found, UntypedEntry):
        return None, None, True
    return found.universe_spec, found.document_type, False


def same_as(one: Entry, other: Entry) -> bool:
    ignored = ("time", "allowed_by")

    def kept(found: Entry) -> dict[str, Any]:
        return {key: value for key, value in plain(found).items() if key not in ignored}

    return kept(one) == kept(other)


Files = dict[str, Entry]


def normal_path(
    path: str, *, pointer: str | None = None, code: str | None = None
) -> str:
    """Strip a leading `./` from a path relative to the knowledge base root folder.

    Raise DocumentTypesError for an absolute path, a backslash, a NUL byte, or an empty, `.` or
    `..` segment.
    """
    trimmed = path.removeprefix("./")
    parts = trimmed.split("/")
    if (
        not trimmed
        or trimmed.startswith("/")
        or "\\" in trimmed
        or "\0" in trimmed
        or any(part in ("", ".", "..") for part in parts)
    ):
        msg = (
            f"Invalid path {path!r}. Use a path relative to the knowledge base root "
            "folder, with `/` separators, such as `docs/rfcs/0042-cache.md`."
        )
        raise DocumentTypesError(msg, code=code, pointer=pointer)
    return trimmed


def is_configuration(path: str) -> bool:
    return CONFIGURATION in path.split("/")[:-1]


def _load(text: str) -> Any:
    try:
        return yaml.safe_load(text) if text.strip() else None
    except yaml.YAMLError as error:
        msg = (
            f"Could not parse {PLACE} as YAML: {error}\n"
            "Correct the YAML, then resend the text as `record`."
        )
        raise _record_error(msg) from error


def is_old(text: str) -> bool:
    data = _load(text)
    return isinstance(data, dict) and data.get("schema") == OLD_SCHEMA


def _migrated(value: Any) -> Any:
    """Rename the fields and values of a 0.2.1 `record.yaml` entry to the current names."""
    if not isinstance(value, dict):
        return value
    renamed = {"kind": "document_type", "no_fit": "no_document_type"}
    entry = {renamed.get(key, key): item for key, item in value.items()}
    if "made" in entry:
        made = entry.pop("made")
        entry["set_by"] = OLD_SET_BY.get(made, made)
    allowed = entry.get("allowed_by")
    if isinstance(allowed, dict) and "basis" in allowed:
        basis = allowed["basis"]
        entry["allowed_by"] = {**allowed, "basis": OLD_BASIS.get(basis, basis)}
    return entry


def _written(value: Any) -> Any:
    """Turn `version` and `time` back into text after YAML parsing."""
    if not isinstance(value, dict):
        return value
    return {
        key: _as_text(item) if key in ("version", "time") else item
        for key, item in value.items()
    }


def parse(text: str) -> Files:
    """Return {} for empty text. For old `record.yaml` text, rename the fields to the current names.

    Raise DocumentTypesError with code `record-invalid` for bad YAML, a wrong `schema`, an invalid
    path, or text that fails document-types.schema.yaml.
    """
    data = _load(text)
    if data is None:
        return {}
    old = isinstance(data, dict) and data.get("schema") == OLD_SCHEMA
    if not isinstance(data, dict) or not (old or data.get("schema") == SCHEMA):
        msg = (
            f"{PLACE} must contain `schema: {SCHEMA}`. Correct the schema field in the file, "
            "then read and resend the file text as `record`."
        )
        raise _record_error(msg)
    found = data.get("files")
    if found is None:
        found = {}
    if isinstance(found, dict):
        try:
            found = {
                normal_path(str(path), pointer=RECORD, code="record-invalid"): _written(
                    _migrated(value) if old else value
                )
                for path, value in found.items()
            }
        except DocumentTypesError as error:
            msg = f"{PLACE}: {error.detail}"
            raise _record_error(msg) from error
    checked = {**data, "schema": SCHEMA, "files": found}
    issues = schemas.record_issues(checked)
    if issues:
        msg = f"{PLACE} is invalid: {'; '.join(issues)}."
        raise _record_error(msg)
    return {path: ENTRY.validate_python(value) for path, value in found.items()}


def dump(files: Files) -> str:
    """Return the file text, with the header first and entries sorted by path."""
    data = {
        "schema": SCHEMA,
        "files": {path: plain(files[path]) for path in sorted(files)},
    }
    body = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )
    return HEADER + body


def lookup(files: Files, folders: list[str], name: str) -> tuple[str, Entry | None]:
    key = normal_path("/".join([*folders, name]))
    return key, files.get(key)


def answer(key: str, found: Entry) -> dict[str, Any]:
    return {"path": key, "label": LABEL, "entry": plain(found)}


Event = tuple[str, str, str | None, str | None]
"""A tuple (change, path, old path, fingerprint)."""


def event(change: FileChange) -> Event:
    """Raise DocumentTypesError for invalid paths."""
    old = normal_path(change.old_path) if isinstance(change, FileMoved) else None
    kind = "fingerprint" if change.change == "edited" else change.change
    fingerprint = None if isinstance(change, FileDeleted) else change.fingerprint
    return (kind, normal_path(change.path), old, fingerprint)


def _paths_by_key(
    paths: list[str], key_of: Callable[[str], str | None]
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for path in paths:
        key = key_of(path)
        if key:
            grouped.setdefault(key, []).append(path)
    return grouped


def compare(files: Files, listing: dict[str, str | None]) -> list[Event]:
    """Return the events that turn the paths in `files` into the paths in `listing`.

    Two passes find moves. Each pass pairs a path missing from `listing` with a path new in
    `listing`. The first pass pairs equal fingerprints. The second pairs equal file names, unless
    both fingerprints are known and differ. A pass pairs paths only when exactly one missing path
    and exactly one new path share the fingerprint or file name. Other missing paths get `deleted`
    events, and other new paths get `created` events. A path in both mappings gets a `fingerprint`
    event only when `listing` supplies a different, nonempty fingerprint.
    """
    gone = [path for path in files if path not in listing]
    new = [path for path in listing if path not in files]
    events: list[Event] = []

    def pair(
        key_of_gone: Callable[[str], str | None],
        key_of_new: Callable[[str], str | None],
        same: Callable[[str, str], bool] | None = None,
    ) -> None:
        by_gone = _paths_by_key(gone, key_of_gone)
        by_new = _paths_by_key(new, key_of_new)
        for key, olds in by_gone.items():
            news = by_new.get(key, [])
            if (
                len(olds) == 1
                and len(news) == 1
                and (same is None or same(olds[0], news[0]))
            ):
                events.append(("moved", news[0], olds[0], listing[news[0]]))
                gone.remove(olds[0])
                new.remove(news[0])

    pair(lambda path: files[path].fingerprint, lambda path: listing[path])

    def same_content(old: str, new: str) -> bool:
        before, after = files[old].fingerprint, listing[new]
        return before is None or after is None or before == after

    pair(posixpath.basename, posixpath.basename, same_content)
    events += [("deleted", path, None, None) for path in gone]
    events += [("created", path, None, listing[path]) for path in new]
    for path, fingerprint in listing.items():
        entry = files.get(path)
        if entry and fingerprint and entry.fingerprint != fingerprint:
            events.append(("fingerprint", path, None, fingerprint))
    return events


def as_change(event: Event) -> dict[str, str]:
    change, path, old, fingerprint = event
    item = {"change": "edited" if change == "fingerprint" else change, "path": path}
    if old is not None:
        item["old_path"] = old
    if fingerprint is not None and change != "deleted":
        item["fingerprint"] = fingerprint
    return item


def keeps_on_move(entry: Entry) -> bool:
    confirmed = entry.audience is not None and entry.audience.status == "confirmed"
    return entry.set_by == "person" or confirmed


def digest(text: str) -> str:
    return log.text_digest(text)


def received_text(
    text: str | None, sent_digest: str | None, recall: Callable[[str], str | None]
) -> str:
    """Return `text`, or the text that `recall` returns for `sent_digest`.

    Raise DocumentTypesError when both `text` and `sent_digest` arrive, when neither arrives, or
    when `recall` has no text for the digest.
    """
    if text is not None and sent_digest is not None:
        msg = "Send `record` or `record_digest`, never both."
        raise DocumentTypesError(msg, pointer=problems.pointer("record_digest"))
    if text is not None:
        return text
    if sent_digest is None:
        msg = (
            f"Send `record` with the text of {PLACE} exactly as read, or empty text when the "
            "file is missing. Or send `record_digest` with the `digest` from an earlier answer in "
            "this session."
        )
        raise DocumentTypesError(msg, pointer=RECORD)
    held = recall(sent_digest)
    if held is None:
        msg = (
            f"This session holds no text for {sent_digest}. Send `record`, the text of "
            f"{PLACE} exactly as read."
        )
        raise DocumentTypesError(
            msg, code="digest-unknown", pointer=problems.pointer("record_digest")
        )
    return held


class SentEntry(Protocol):
    path: str
    set_by: SetBy
    universe_spec: str | None
    document_type: str | None
    no_document_type: bool
    audience: Audience | None


Kinds = dict[str, tuple[str, frozenset[str]]]
"""Universe spec id to (version, document type ids), for the universe specs that apply at one path."""


@dataclass
class Pending:
    path: str
    was: Entry | None = None
    old_path: str | None = None


@dataclass
class Merged:
    files: Files
    changed: list[dict[str, Any]] = field(default_factory=list)
    settle: dict[str, Pending] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeRequest:
    events: list[Event]
    entries: Sequence[SentEntry]
    recheck: bool
    kinds_at: Callable[[str], Kinds]
    allowed_by: AllowedBy | None
    fingerprints: dict[str, str]


def merge(files: Files, sent: MergeRequest) -> Merged:
    """Apply the file changes, then `recheck`, then the sent entries, to a copy of `files`.

    `recheck` adds every file whose entry has `set_by: agent` to `settle`. Entries the person set
    override later entries by the agent. merge stores nonempty event fingerprints in
    `sent.fingerprints`. Later document type entries use stored fingerprints, including across
    calls that share the dictionary. Audience-only updates retain the existing fingerprint.
    """
    out = Merged(files=dict(files))
    for event in sent.events:
        _apply(out, event, sent.kinds_at, sent.fingerprints)
    if sent.recheck:
        for path, entry in out.files.items():
            if entry.set_by != "person":
                out.settle.setdefault(path, Pending(path, was=entry))
    now = log.now()
    for index, item in enumerate(sent.entries):
        _apply_entry(out, index, item, sent, now)
    return out


def _apply(
    out: Merged, event: Event, kinds_at: Callable[[str], Kinds], prints: dict[str, str]
) -> None:
    change, path, _old, fingerprint = event
    if fingerprint:
        prints[path] = fingerprint
    files = out.files
    if change == "fingerprint" or (change == "created" and path in files):
        found = files.get(path)
        if found and fingerprint and found.fingerprint != fingerprint:
            files[path] = found.model_copy(update={"fingerprint": fingerprint})
            out.changed.append(
                {"path": path, "change": "fingerprint", "entry": plain(files[path])}
            )
        return
    if change == "created":
        out.settle.setdefault(path, Pending(path))
        return
    if change == "deleted":
        out.settle.pop(path, None)
        found = files.pop(path, None)
        if found is not None:
            _deleted(out, path, found)
        return
    _move(out, event, kinds_at)


def _move(out: Merged, event: Event, kinds_at: Callable[[str], Kinds]) -> None:
    _, path, old, fingerprint = event
    files = out.files
    # Only `moved` events reach this function, and they always hold the old path.
    assert old is not None
    out.settle.pop(old, None)
    found = files.pop(old, None)
    if found is None:
        if path not in files:
            out.settle.setdefault(path, Pending(path, old_path=old))
        return
    if path in files:
        _deleted(out, old, found)
        return
    moved = found.model_copy(update={"fingerprint": fingerprint or found.fingerprint})
    if keeps_on_move(found) and (
        isinstance(found, UntypedEntry) or found.universe_spec in kinds_at(path)
    ):
        files[path] = moved
        out.changed.append(
            {"path": path, "change": "moved", "old_path": old, "entry": plain(moved)}
        )
        return
    out.changed.append(
        {"path": path, "change": "moved", "old_path": old, "was": plain(found)}
    )
    out.settle[path] = Pending(path, was=found, old_path=old)


def _deleted(out: Merged, path: str, found: Entry) -> None:
    change: dict[str, Any] = {"path": path, "change": "deleted", "was": plain(found)}
    if keeps_on_move(found):
        change["note"] = (
            "The person set this entry or confirmed the file's reader. If the file "
            "now has another path, ask the person whether the entry still applies, then send "
            "the entry for the new path with `set_by: person`."
        )
    out.changed.append(change)


def _apply_entry(
    out: Merged, index: int, item: SentEntry, sent: MergeRequest, now: str
) -> None:
    kinds_at, allowed_by, prints = sent.kinds_at, sent.allowed_by, sent.fingerprints
    at = ("entries", index)
    path = normal_path(item.path, pointer=problems.pointer(*at, "path"))
    current = out.files.get(path)
    if item.set_by == "agent" and current is not None and current.set_by == "person":
        out.settle.pop(path, None)
        out.changed.append(
            {
                "path": path,
                "change": "kept",
                "entry": plain(current),
                "note": "The person set this entry, so it overrides the agent's entry.",
            }
        )
        return
    names_type = item.universe_spec is not None or item.document_type is not None
    if not names_type and not item.no_document_type:
        if item.audience is None or current is None:
            msg = (
                f"The entry for {path} names no document type. Send `universe_spec` and "
                "`document_type`, or `no_document_type: true`. Send `audience` alone only for "
                "a file that already has an entry."
            )
            raise DocumentTypesError(msg, pointer=problems.pointer(*at))
        set_by = "person" if item.set_by == "person" else current.set_by
        new: Entry = current.model_copy(
            update={
                "audience": item.audience,
                "set_by": set_by,
                "allowed_by": allowed_by,
                "time": now,
            }
        )
    else:
        if item.no_document_type and names_type:
            msg = (
                f"The entry for {path} has both `no_document_type` and a document type. Send "
                "either `no_document_type` or the document type."
            )
            raise DocumentTypesError(
                msg, pointer=problems.pointer(*at, "no_document_type")
            )
        audience = item.audience
        same_type = current is not None and named(current) == (
            item.universe_spec,
            item.document_type,
            bool(item.no_document_type),
        )
        if audience is None and same_type and current is not None:
            audience = current.audience
        fingerprint = prints.get(path) or (current.fingerprint if current else None)
        if item.no_document_type:
            new = UntypedEntry(
                no_document_type=True,
                audience=audience,
                set_by=item.set_by,
                allowed_by=allowed_by,
                fingerprint=fingerprint,
                time=now,
            )
        else:
            universe_spec, document_type, version = _version(
                path, index, item, kinds_at(path)
            )
            new = TypedEntry(
                universe_spec=universe_spec,
                version=version,
                document_type=document_type,
                audience=audience,
                set_by=item.set_by,
                allowed_by=allowed_by,
                fingerprint=fingerprint,
                time=now,
            )
    out.settle.pop(path, None)
    if current is not None and same_as(current, new):
        return
    out.files[path] = new
    change = {
        "path": path,
        "change": "corrected" if item.set_by == "person" else "settled",
        "entry": plain(new),
    }
    if current is not None:
        change["was"] = plain(current)
    out.changed.append(change)


def _version(
    path: str, index: int, item: SentEntry, kinds: Kinds
) -> tuple[str, str, str]:
    """Return the entry's universe spec, document type and version.

    Raise DocumentTypesError when `universe_spec` or `document_type` is missing, when
    `universe_spec` does not apply at the path, or when `universe_spec` has no document type named
    `document_type`.
    """
    if item.universe_spec is None or item.document_type is None:
        msg = (
            f"The entry for {path} names only one of `universe_spec` and `document_type`. "
            "Send both fields."
        )
        missing = "document_type" if item.document_type is None else "universe_spec"
        raise DocumentTypesError(
            msg, pointer=problems.pointer("entries", index, missing)
        )
    found = kinds.get(item.universe_spec)
    if found is None or item.document_type not in found[1]:
        applying = ", ".join(sorted(kinds)) or "none"
        msg = (
            f"Universe spec {item.universe_spec!r} has no document type "
            f"{item.document_type!r} at {path}. Universe specs that apply at {path}: "
            f"{applying}. Pick a document type from this file's `candidates` in an "
            "earlier answer, or from the `kbp_kinds` output."
        )
        raise DocumentTypesError(
            msg,
            code="document-type-unknown",
            pointer=problems.pointer("entries", index, "document_type"),
        )
    return item.universe_spec, item.document_type, found[0]
