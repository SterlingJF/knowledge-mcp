"""The fit record: which universe spec and document type each file of a knowledge base is.

The record lives in the knowledge base at `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, a
plugin folder inside the top folder's `.knowledge-bus/`, which the host reads and writes, creating
the folders when missing. `kbp` reads only the definitions directly inside `.knowledge-bus/`, so
the record changes no universe spec in scope. knowledge-mcp reads the text the host sends, merges
the file changes and the fits into the entries, and returns the merged text. A person's correction wins over any later fit by the
agent. Nothing here opens a file.
"""

from __future__ import annotations

import posixpath
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal, Protocol

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from knowledge_mcp import log

SCHEMA = "knowledge-mcp/fit-record/1"
UPDATE = "knowledge-mcp/fit-record-update/1"
PLACE = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"
LABEL = "from the record"
NO_FIT = "no fit"

HEADER = """\
# The fit record: which universe spec and document type each file of this knowledge base is.
# Your agent keeps the record through knowledge-mcp as files are created, moved and deleted.
# A person's correction wins over any later fit by the agent.
"""

# The folder whose files are configuration for a knowledge base, the record included, never
# documents in it.
CONFIGURATION = ".knowledge-bus"

Basis = Literal["request", "line", "change_row"]
Made = Literal["fit", "correction"]


class RecordError(ValueError):
    """The record or a change can't be used; the message says what to send instead."""


def _as_text(value: Any) -> Any:
    """A version or time as written, when YAML read the value as a number or a date."""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return value


class Audience(BaseModel):
    """The document's reader, and whether the person confirmed the value."""

    model_config = ConfigDict(extra="forbid")

    value: str
    status: Literal["confirmed", "guessed"]


class AllowedBy(BaseModel):
    """The request, standing line or accepted change row that allowed the save."""

    model_config = ConfigDict(extra="forbid")

    basis: Basis
    text: str
    location: str | None = None


class Entry(BaseModel):
    """One file's fit: a universe spec and document type, or "no fit"."""

    model_config = ConfigDict(extra="forbid")

    universe_spec: str | None = None
    version: str | None = None
    kind: str | None = None
    no_fit: Literal[True] | None = None
    audience: Audience | None = None
    made: Made
    allowed_by: AllowedBy | None = None
    fingerprint: str | None = None
    time: str

    @field_validator("version", "time", mode="before")
    @classmethod
    def _written(cls, value: Any) -> Any:
        return _as_text(value)

    @model_validator(mode="after")
    def _fit_or_no_fit(self) -> Entry:
        named = (self.universe_spec, self.version, self.kind)
        if self.no_fit:
            if any(part is not None for part in named):
                msg = (
                    "For `no_fit: true`, omit `universe_spec`, `version` and `kind`, "
                    "or set each field to null."
                )
                raise ValueError(msg)
        elif any(part is None for part in named):
            msg = (
                "Provide `universe_spec`, `version` and `kind`, or set `no_fit: true`."
            )
            raise ValueError(msg)
        return self

    def fit(self) -> tuple[str | None, str | None, bool]:
        return self.universe_spec, self.kind, bool(self.no_fit)

    def plain(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    def same_as(self, other: Entry) -> bool:
        """The same fit, reader, maker and fingerprint, whatever the time and the basis."""
        ignored = {"time", "allowed_by"}
        return self.model_dump(exclude=ignored) == other.model_dump(exclude=ignored)


Files = dict[str, Entry]


def normal_path(path: str) -> str:
    """The path from the knowledge base's top folder, with `/` between folders."""
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
            f"Invalid record path {path!r}. Use a path relative to the knowledge base's top "
            "folder with `/` separators, such as `docs/rfcs/0042-cache.md`."
        )
        raise RecordError(msg)
    return trimmed


def is_configuration(path: str) -> bool:
    return CONFIGURATION in path.split("/")[:-1]


def parse(text: str) -> Files:
    """The entries in a record's text; empty text is an empty record."""
    try:
        data = yaml.safe_load(text) if text.strip() else None
    except yaml.YAMLError as error:
        msg = f"Could not parse {PLACE} as YAML: {error}"
        raise RecordError(msg) from error
    if data is None:
        return {}
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        msg = (
            f"{PLACE} must contain `schema: {SCHEMA}`; send the record's text as read."
        )
        raise RecordError(msg)
    unknown = set(data) - {"schema", "files"}
    if unknown:
        msg = f"{PLACE} holds unknown keys: {', '.join(sorted(unknown))}."
        raise RecordError(msg)
    files: Files = {}
    for path, value in (data.get("files") or {}).items():
        key = normal_path(str(path))
        try:
            entry = Entry.model_validate(value)
        except ValidationError as error:
            msg = f"{PLACE}: invalid fit record entry for {key}: {error}"
            raise RecordError(msg) from error
        if entry.allowed_by is None:
            msg = f"{PLACE}: missing `allowed_by` for entry {key}."
            raise RecordError(msg)
        files[key] = entry
    return files


def dump(files: Files) -> str:
    """The record's text: the header, then one entry per file, paths in order."""
    data = {
        "schema": SCHEMA,
        "files": {path: files[path].plain() for path in sorted(files)},
    }
    body = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )
    return HEADER + body


def lookup(files: Files, folders: list[str], name: str) -> tuple[str, Entry | None]:
    """The record key for a file, and its entry when recorded."""
    key = normal_path("/".join([*folders, name]))
    return key, files.get(key)


def answer(key: str, entry: Entry) -> dict[str, Any]:
    """A recorded file's answer, labelled as coming from the record."""
    return {"path": key, "label": LABEL, **entry.plain()}


# --- Changes ---------------------------------------------------------------

Event = tuple[str, str, str | None, str | None]
"""(change, path, old path, fingerprint): `created`, `deleted`, `moved` or `fingerprint`."""


def compare(files: Files, listing: dict[str, str | None]) -> list[Event]:
    """The changes that turn the record's files into the listed files.

    A recorded file missing from the listing and a listed file missing from the record make one
    move when their fingerprints match, else when they share a file name that no other such file
    has and carry no two different fingerprints. Every other missing file is deleted, every other
    new file created.
    """
    gone = [path for path in files if path not in listing]
    new = [path for path in listing if path not in files]
    events: list[Event] = []

    def pair(
        key_of_gone: Any, key_of_new: Any, same: Any = lambda old, new: True
    ) -> None:
        by_gone: dict[str, list[str]] = {}
        by_new: dict[str, list[str]] = {}
        for path in gone:
            key = key_of_gone(path)
            if key:
                by_gone.setdefault(key, []).append(path)
        for path in new:
            key = key_of_new(path)
            if key:
                by_new.setdefault(key, []).append(path)
        for key, olds in by_gone.items():
            news = by_new.get(key, [])
            if len(olds) == 1 and len(news) == 1 and same(olds[0], news[0]):
                events.append(("moved", news[0], olds[0], listing[news[0]]))
                gone.remove(olds[0])
                new.remove(news[0])

    pair(lambda path: files[path].fingerprint, lambda path: listing[path])

    def same_content(old: str, new: str) -> bool:
        # Two different fingerprints mean different content, whatever the file names.
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
    """An event as the host sends a change in `changes`."""
    change, path, old, fingerprint = event
    item = {"change": "edited" if change == "fingerprint" else change, "path": path}
    if old is not None:
        item["old_path"] = old
    if fingerprint is not None and change != "deleted":
        item["fingerprint"] = fingerprint
    return item


def keeps_on_move(entry: Entry) -> bool:
    """A person's correction or confirmed reader moves with the file; a plain fit is redone."""
    confirmed = entry.audience is not None and entry.audience.status == "confirmed"
    return entry.made == "correction" or confirmed


def digest(text: str) -> str:
    return log.text_digest(text)


def received_text(
    text: str | None, sent_digest: str | None, recall: Callable[[str], str | None]
) -> str:
    """The record's text: as sent, or the text this session holds for the digest sent."""
    if text is not None and sent_digest is not None:
        msg = "Send the record's text or its digest, never both."
        raise RecordError(msg)
    if text is not None:
        return text
    if sent_digest is None:
        msg = (
            f"Send the text of {PLACE} as read, an empty text when the file is missing, or the "
            "digest an earlier answer in this session returned."
        )
        raise RecordError(msg)
    held = recall(sent_digest)
    if held is None:
        msg = (
            f"This session holds no record text for {sent_digest}: send the text of {PLACE} "
            "as read."
        )
        raise RecordError(msg)
    return held


class Fit(Protocol):
    """One fit the agent settled or a correction the person stated, as the host sends it."""

    path: str
    made: Made
    universe_spec: str | None
    kind: str | None
    no_fit: bool
    audience: Audience | None


Kinds = dict[str, tuple[str, frozenset[str]]]
"""Universe spec id to its version and document type ids, in scope at one path."""


@dataclass
class Settle:
    """A file waiting for the agent to settle its fit."""

    path: str
    was: Entry | None = None
    old_path: str | None = None


@dataclass
class Merged:
    files: Files
    changed: list[dict[str, Any]] = field(default_factory=list)
    settle: dict[str, Settle] = field(default_factory=dict)


def merge(
    files: Files,
    *,
    events: list[Event],
    fits: list[Fit],
    refit: bool,
    kinds_at: Callable[[str], Kinds],
    allowed_by: AllowedBy | None,
    fingerprints: dict[str, str],
) -> Merged:
    """Apply the file changes, then the fits, to a copy of the record's files.

    `fingerprints` holds the fingerprints seen this session; new ones are added to it, so a file
    settled in a later call keeps the fingerprint its listing gave.
    """
    out = Merged(files=dict(files))
    for event in events:
        _apply(out, event, kinds_at, fingerprints)
    if refit:
        for path, entry in out.files.items():
            if entry.made != "correction":
                out.settle.setdefault(path, Settle(path, was=entry))
    now = log.now()
    for item in fits:
        _settle(out, item, kinds_at, allowed_by, fingerprints, now)
    return out


def _apply(
    out: Merged, event: Event, kinds_at: Callable[[str], Kinds], prints: dict[str, str]
) -> None:
    change, path, old, fingerprint = event
    if fingerprint:
        prints[path] = fingerprint
    files = out.files
    if change == "fingerprint" or (change == "created" and path in files):
        entry = files.get(path)
        if entry and fingerprint and entry.fingerprint != fingerprint:
            files[path] = entry.model_copy(update={"fingerprint": fingerprint})
            out.changed.append(
                {"path": path, "change": "fingerprint", "entry": files[path].plain()}
            )
        return
    if change == "created":
        out.settle.setdefault(path, Settle(path))
        return
    if change == "deleted":
        out.settle.pop(path, None)
        entry = files.pop(path, None)
        if entry is not None:
            _deleted(out, path, entry)
        return
    # Moved: `old` is the path before the move.
    assert old is not None
    out.settle.pop(old, None)
    entry = files.pop(old, None)
    if entry is None:
        if path not in files:
            out.settle.setdefault(path, Settle(path, old_path=old))
        return
    if path in files:
        _deleted(out, old, entry)
        return
    moved = entry.model_copy(update={"fingerprint": fingerprint or entry.fingerprint})
    if keeps_on_move(entry) and (entry.no_fit or entry.universe_spec in kinds_at(path)):
        files[path] = moved
        out.changed.append(
            {"path": path, "change": "moved", "old_path": old, "entry": moved.plain()}
        )
        return
    out.changed.append(
        {"path": path, "change": "moved", "old_path": old, "was": entry.plain()}
    )
    out.settle[path] = Settle(path, was=entry, old_path=old)


def _deleted(out: Merged, path: str, entry: Entry) -> None:
    change: dict[str, Any] = {"path": path, "change": "deleted", "was": entry.plain()}
    if keeps_on_move(entry):
        change["note"] = (
            "The entry held the person's correction or confirmed reader. When the file lives "
            "on under another path, ask the person, then send the entry as a correction for "
            "the new path."
        )
    out.changed.append(change)


def _settle(
    out: Merged,
    item: Fit,
    kinds_at: Callable[[str], Kinds],
    allowed_by: AllowedBy | None,
    prints: dict[str, str],
    now: str,
) -> None:
    path = normal_path(item.path)
    current = out.files.get(path)
    if item.made == "fit" and current is not None and current.made == "correction":
        out.settle.pop(path, None)
        out.changed.append(
            {
                "path": path,
                "change": "kept",
                "entry": current.plain(),
                "note": "The person's correction wins over a fit by the agent.",
            }
        )
        return
    named = item.universe_spec is not None or item.kind is not None
    if not named and not item.no_fit:
        if item.audience is None or current is None:
            msg = (
                f"The fit for {path} names no document type: send `universe_spec` and `kind`, "
                "or `no_fit`, or `audience` alone for a file the record holds."
            )
            raise RecordError(msg)
        made = "correction" if item.made == "correction" else current.made
        new = current.model_copy(
            update={
                "audience": item.audience,
                "made": made,
                "allowed_by": allowed_by,
                "time": now,
            }
        )
    else:
        if item.no_fit and named:
            msg = f"The fit for {path} holds `no_fit` and a document type: send one of the two."
            raise RecordError(msg)
        version = None
        if not item.no_fit:
            version = _version(path, item, kinds_at(path))
        audience = item.audience
        same_type = current is not None and current.fit() == (
            item.universe_spec,
            item.kind,
            bool(item.no_fit),
        )
        if audience is None and same_type:
            # A fit to the same document type keeps the reader already recorded.
            audience = current.audience
        new = Entry(
            universe_spec=item.universe_spec,
            version=version,
            kind=item.kind,
            no_fit=True if item.no_fit else None,
            audience=audience,
            made=item.made,
            allowed_by=allowed_by,
            fingerprint=prints.get(path) or (current.fingerprint if current else None),
            time=now,
        )
    out.settle.pop(path, None)
    if current is not None and current.same_as(new):
        return
    out.files[path] = new
    change = {
        "path": path,
        "change": "corrected" if item.made == "correction" else "fitted",
        "entry": new.plain(),
    }
    if current is not None:
        change["was"] = current.plain()
    out.changed.append(change)


def _version(path: str, item: Fit, kinds: Kinds) -> str:
    if item.universe_spec is None or item.kind is None:
        msg = f"The fit for {path} names a document type: send both `universe_spec` and `kind`."
        raise RecordError(msg)
    found = kinds.get(item.universe_spec)
    if found is None or item.kind not in found[1]:
        in_scope = ", ".join(sorted(kinds)) or "none"
        msg = (
            f"No document type {item.kind!r} in universe spec {item.universe_spec!r} at {path}; "
            f"universe specs in scope there: {in_scope}. Pick a candidate the answer lists, or "
            "one that `kbp_kinds` lists."
        )
        raise RecordError(msg)
    return found[0]
