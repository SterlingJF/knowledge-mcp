from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from knowledge_mcp import document_type, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.models import (
    AllowedBy,
    EntryItem,
    FileChange,
    KnowledgeBusFolder,
    ListedFile,
    ScopeRequest,
)
from knowledge_mcp.models_auto.document_types_update_schema import (
    DocumentTypesUpdateAnswer,
)
from knowledge_mcp.scope import ScopeError, Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.document_type import (
    RecordDigest,
    RecordText,
    kinds_of,
    listed_kinds,
    scope_specs,
)

DESCRIPTION = """\
Prepare document-types text from `record` or `record_digest`, file changes and `entries`, returning changed entries and files needing a document type. Include `allowed_by` to receive text when entries change or migration requires saving. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""

MIGRATED = (
    f"Save `record` as `{records.PLACE}` in place of `{records.OLD_PLACE}`. "
    f"Delete `{records.OLD_PLACE}` only with the person's permission."
)


@dataclass
class Scope:
    index: int
    listing: dict[str, Any]
    specs: list[dict[str, Any]]
    kinds: records.Kinds
    wants_every: bool = False


@dataclass
class Scopes:
    """Run `kbp --kinds` once for each set of `.knowledge-bus/` folders that apply to a file,
    and cache each result.

    Raise ScopeError when `knowledge_bus_folders` names a folder more than once.
    """

    workspace: Workspace
    folders: list[KnowledgeBusFolder]
    found: dict[tuple[tuple[str, ...], ...], Scope] = field(default_factory=dict)
    received: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        seen = set()
        for index, item in enumerate(self.folders):
            parts = _parts(item.folder, index)
            if parts in seen:
                msg = (
                    f"Send each folder once in `knowledge_bus_folders`. {item.folder!r} "
                    "appears more than once."
                )
                raise ScopeError(
                    msg,
                    pointer=problems.pointer("knowledge_bus_folders", index, "folder"),
                )
            seen.add(parts)

    def at(self, path: str) -> Scope:
        chain = path.split("/")[:-1]
        applicable = sorted(
            (
                (_parts(item.folder, index), index, item)
                for index, item in enumerate(self.folders)
                if list(_parts(item.folder, index))
                == chain[: len(_parts(item.folder, index))]
            ),
            key=lambda found: len(found[0]),
        )
        key = tuple(parts for parts, _, _ in applicable)
        if key in self.found:
            return self.found[key]
        request = ScopeRequest(
            folders=list(applicable[-1][0]) if applicable else [],
            knowledge_bus_folders=[item for _, _, item in applicable],
            positions=[index for _, index, _ in applicable],
        )
        listing, rebuilt = listed_kinds(self.workspace, request)
        for item in rebuilt.received:
            self.received[str(item["digest"])] = item
        scope = Scope(
            len(self.found), listing, scope_specs(listing, rebuilt), kinds_of(listing)
        )
        self.found[key] = scope
        return scope

    def kinds_at(self, path: str) -> records.Kinds:
        return self.at(path).kinds


def _parts(folder: str, index: int) -> tuple[str, ...]:
    if folder in ("", "."):
        return ()
    pointer = problems.pointer("knowledge_bus_folders", index, "folder")
    return tuple(records.normal_path(folder, pointer=pointer).split("/"))


def _listing_events(
    files: records.Files, listing: list[ListedFile] | None
) -> list[records.Event] | None:
    """Skip paths under any `.knowledge-bus/` folder. Raise DocumentTypesError for an invalid
    listed path.
    """
    if listing is None:
        return None
    listed: dict[str, str | None] = {}
    for index, item in enumerate(listing):
        pointer = problems.pointer("listing", index, "path")
        path = records.normal_path(item.path, pointer=pointer)
        if not records.is_configuration(path):
            listed[path] = item.fingerprint
    return records.compare(files, listed)


def _to_settle(merged: records.Merged, scopes: Scopes) -> list[dict[str, Any]]:
    """When a file name matches no document type, set `wants_every` on the file's `Scope` so the
    answer lists every document type in that `Scope`.
    """
    to_settle = []
    for waiting in merged.settle.values():
        scope = scopes.at(waiting.path)
        folder, name = posixpath.split(waiting.path)
        found = document_type.answer(
            scope.listing,
            document_type.MatchRequest(
                location=waiting.path,
                name=name,
                folders=folder.split("/") if folder else [],
                role=None,
                universe_specs=scope.specs,
            ),
        )
        if found["every_document_type"] is not None:
            scope.wants_every = True
        item: dict[str, Any] = {
            "path": waiting.path,
            "scope": scope.index,
            "candidates": found["candidates"],
        }
        if waiting.old_path is not None:
            item["old_path"] = waiting.old_path
        if waiting.was is not None:
            item["was"] = records.plain(waiting.was)
        to_settle.append(item)
    return to_settle


@dataclass(frozen=True)
class Request:
    location: str
    folders: list[KnowledgeBusFolder]
    listing: list[ListedFile] | None
    changes: list[FileChange] | None
    entries: list[EntryItem]
    recheck: bool
    allowed_by: AllowedBy | None


def _merge(workspace: Workspace, text: str, sent: Request) -> dict[str, Any]:
    files = records.parse(text)
    migrated = records.is_old(text)
    based_on = workspace.remember(text)
    scopes = Scopes(workspace, sent.folders)
    from_listing = _listing_events(files, sent.listing)
    merged = records.merge(
        files,
        records.MergeRequest(
            events=(from_listing or [])
            + [records.event(change) for change in sent.changes or []],
            entries=sent.entries,
            recheck=sent.recheck,
            kinds_at=scopes.kinds_at,
            allowed_by=sent.allowed_by,
            fingerprints=workspace.fingerprints.setdefault(sent.location, {}),
        ),
    )
    to_settle = _to_settle(merged, scopes)

    changed = migrated or {
        path: records.plain(entry) for path, entry in merged.files.items()
    } != {path: records.plain(entry) for path, entry in files.items()}
    saved = None
    if changed and sent.allowed_by is not None:
        saved = records.dump(merged.files)
        workspace.remember(saved)

    result: dict[str, Any] = {
        "schema": records.UPDATE,
        "location": sent.location,
        "based_on": based_on,
        "record": saved,
        "digest": records.digest(saved) if saved is not None else None,
        "changed": merged.changed,
        "to_settle": to_settle,
        "scopes": [
            {
                "universe_specs": scope.specs,
                "every_document_type": document_type.every(scope.listing)
                if scope.wants_every
                else None,
            }
            for scope in sorted(scopes.found.values(), key=lambda scope: scope.index)
        ],
        "received": list(scopes.received.values()),
    }
    if from_listing is not None:
        result["listing_changes"] = [records.as_change(event) for event in from_listing]
    if changed and sent.allowed_by is None:
        result["note"] = (
            "`record` is null because the call sent no `allowed_by`. "
            "Follow `kb-track-document-types` to supply permission and save the result."
        )
    elif saved is not None and migrated:
        result["note"] = MIGRATED
    return result


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_prepare_document_types",
        title="Prepare the document-types file",
        description=DESCRIPTION,
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    def kb_prepare_document_types(
        location: Annotated[
            str,
            Field(
                description=(
                    "The knowledge base root folder as plain text, such as a local path, a "
                    "Drive folder link or a Notion page. knowledge-mcp logs this text and never "
                    "opens the location."
                )
            ),
        ],
        record: RecordText = None,
        record_digest: RecordDigest = None,
        knowledge_bus_folders: Annotated[
            list[KnowledgeBusFolder],
            Field(
                description=(
                    "Every knowledge base folder that holds a `.knowledge-bus/` folder, even one "
                    "with no `*.kbp.yaml` file. The bundled universe specs apply to a file when no "
                    "`.knowledge-bus/` folder between the root and the file holds a `*.kbp.yaml` "
                    "file or `workspace.yaml`."
                )
            ),
        ] = [],  # noqa: B006 - pydantic copies the default for each call.
        listing: Annotated[
            list[ListedFile] | None,
            Field(
                description=(
                    "Every file of the knowledge base outside `.knowledge-bus/` folders."
                )
            ),
        ] = None,
        changes: Annotated[
            list[FileChange] | None,
            Field(
                description="Files changed since the document-types file was last saved."
            ),
        ] = None,
        entries: Annotated[
            list[EntryItem] | None,
            Field(
                description=(
                    "Send your document type choices and any document types or readers "
                    "specified by the person."
                )
            ),
        ] = None,
        recheck: Annotated[
            bool | None,
            Field(
                description=(
                    "True to put every file with an entry back in `to_settle`, except files "
                    "with a `set_by: person` entry."
                )
            ),
        ] = None,
        allowed_by: AllowedBy | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            record=record,
            record_digest=record_digest,
            knowledge_bus_folders=knowledge_bus_folders or None,
            listing=listing,
            changes=changes,
            entries=entries,
            recheck=recheck,
            allowed_by=allowed_by,
        )
        text = records.received_text(record, record_digest, workspace.recall)
        sent = Request(
            location=location,
            folders=knowledge_bus_folders,
            listing=listing,
            changes=changes,
            entries=entries or [],
            recheck=bool(recheck),
            allowed_by=allowed_by,
        )
        result = _merge(workspace, text, sent)
        if record is not None:
            result["received"].append(
                {"name": records.PLACE, "digest": result["based_on"]}
            )
        return respond.answer(
            "kb_prepare_document_types",
            location,
            arguments,
            DocumentTypesUpdateAnswer,
            result,
        )
