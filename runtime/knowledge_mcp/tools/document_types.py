from __future__ import annotations

import posixpath
from dataclasses import dataclass
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from knowledge_mcp import conventions as naming
from knowledge_mcp import document_type, filing, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.models import (
    AllowedBy,
    EntryItem,
    FileChange,
    KnowledgeBusFolder,
    ListedFile,
)
from knowledge_mcp.models_auto.common_schema import FilingValue
from knowledge_mcp.models_auto.document_types_update_schema import (
    DocumentTypesUpdateAnswer,
)
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.conventions import ConventionsDigest, ConventionsText
from knowledge_mcp.tools.document_type import (
    RecordDigest,
    RecordText,
)
from knowledge_mcp.type_scope import Scopes

DESCRIPTION = """\
Prepare document-types text and filing assessments from supplied configuration, file changes and entries. Include `allowed_by` to receive changed text. Append the answer to `log.jsonl` and open no knowledge-base file.
"""

MIGRATED = (
    f"Save `record` as `{records.PLACE}` in place of `{records.OLD_PLACE}`. "
    f"Delete `{records.OLD_PLACE}` only with the person's permission."
)


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
    conventions: str | None = None
    conventions_digest: str | None = None
    filing_values: list[FilingValue] | None = None


def _merge(workspace: Workspace, text: str, sent: Request) -> dict[str, Any]:
    convention = naming.Filing.read(
        workspace, sent.conventions, sent.conventions_digest, sent.filing_values
    )
    files = records.parse(text)
    migrated = records.is_old(text)
    based_on = workspace.remember(text)
    scopes = Scopes(workspace, sent.folders, conventions=convention)
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
    current = filing.inventory(workspace, sent.location, sent.listing, sent.changes)
    assessments = {}
    for path, entry in merged.files.items():
        universe, kind, _ = records.named(entry)
        assessments[(path, universe or "", kind or "")] = filing.assess(
            path,
            (universe, kind),
            merged.files,
            listing=current,
            scopes=scopes,
        )
    for item in to_settle:
        scope = scopes.at(item["path"])
        found = {
            "candidates": item["candidates"],
            "every_document_type": None
            if any(c["matched_on"] == "name" for c in item["candidates"])
            else document_type.every(scope.listing),
        }
        for universe, kind in filing.choices(found):
            assessments[(item["path"], universe or "", kind or "")] = filing.assess(
                item["path"],
                (universe, kind),
                merged.files,
                listing=current,
                scopes=scopes,
            )

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
        "filing": [assessments[key] for key in sorted(assessments)],
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
    if sent.conventions is not None:
        result["received"].append({"name": naming.PLACE, "digest": convention.digest})
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
        conventions: ConventionsText = None,
        conventions_digest: ConventionsDigest = None,
        filing_values: list[FilingValue] | None = None,
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
            conventions=conventions,
            conventions_digest=conventions_digest,
            filing_values=filing_values,
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
            conventions=conventions,
            conventions_digest=conventions_digest,
            filing_values=filing_values,
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
