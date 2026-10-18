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
from knowledge_mcp.models_auto.common_schema import (
    ConventionFile,
    FilingReview,
    FilingValue,
)
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
    conventions_files: list[ConventionFile] | None = None
    filing_values: list[FilingValue] | None = None
    filing_review: FilingReview | None = None


def _review_question(row: dict[str, Any]) -> str:
    questions = {
        "values_needed": "Supply the naming values listed in needed.",
        "destination_occupied": "Choose an unoccupied destination or explicitly drop the blocked row.",
        "destination_type_conflict": "Choose a folder with the saved universe spec and document type.",
        "no_peers": "Choose a folder or supply recorded peers for this document type.",
        "no_document_type": "Choose a document type before proposing a move.",
        "evidence_incomplete": "Supply the missing peer-folder definitions.",
        "listing_needed": "Supply the complete inventory.",
    }
    return questions.get(row["status"], "Choose the document type for this file.")


def _review(
    sent: Request,
    assessments: dict[tuple[str, str, str], dict[str, Any]],
    current: list[ListedFile] | None,
    to_settle: list[dict[str, Any]],
    scopes: Scopes,
    files: records.Files,
) -> dict[str, Any] | None:
    review: dict[str, Any] | None = None
    if sent.filing_review is not None:
        recursive = sent.filing_review.recursive
        folder = sent.filing_review.folder
        if folder:
            folder = records.normal_path(folder)

        def selected(path: str) -> bool:
            return (
                (not folder or path.startswith(folder + "/"))
                if recursive
                else posixpath.dirname(path) == folder
            )

        waiting = {item["path"] for item in to_settle}
        rows = [
            filing.assess(
                k[0],
                (k[1] or None, k[2] or None),
                files,
                listing=current,
                scopes=scopes,
                provisional=True,
            )
            for k in sorted(assessments)
            if selected(k[0]) and k[0] not in waiting
        ]
        values = {
            (v.path, v.universe_spec, v.document_type): v
            for v in sent.filing_values or []
        }
        for row in rows:
            value = values.get(
                (row["path"], row["universe_spec"], row["document_type"])
            )
            if value is not None:
                row["values"] = value.model_dump(mode="json", exclude_unset=True)
        filing.review_occupancy(rows, {i.path for i in current or []})
        review = dict(
            folder=folder,
            recursive=recursive,
            assessments=rows,
            unresolved=[],
        )
        seen = set()
        for row in rows:
            if row["status"] not in ("proposed", "already_matches"):
                review["unresolved"].append(
                    dict(
                        path=row["path"],
                        question=_review_question(row),
                    )
                )
            seen.add(row["path"])
        for item in to_settle:
            if selected(item["path"]) and item["path"] not in seen:
                review["unresolved"].append(
                    dict(
                        path=item["path"],
                        question="Choose the document type for this file.",
                    )
                )
        review["unresolved"].sort(key=lambda r: r["path"])

    return review


def _include_review(result: dict[str, Any], review: dict[str, Any] | None) -> None:
    if review is not None:
        result["filing_review"] = review


def _merge(workspace: Workspace, text: str, sent: Request) -> dict[str, Any]:
    scopes = Scopes(workspace, sent.folders)
    convention = naming.Filing.read(
        workspace,
        sent.conventions,
        sent.conventions_digest,
        sent.filing_values,
        naming.Context(workspace, scopes, sent.conventions_files)
        if sent.conventions_files is not None
        else None,
    )
    files = records.parse(text)
    migrated = records.is_old(text)
    based_on = workspace.remember(text)
    scopes.conventions = convention
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
            provisional=False,
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
                provisional=False,
            )

    review = _review(sent, assessments, current, to_settle, scopes, merged.files)

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
    _include_review(result, review)
    if convention.context is not None:
        result["received"].extend(convention.context.received.values())
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
        conventions_files: list[ConventionFile] | None = None,
        filing_review: FilingReview | None = None,
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
            conventions_files=conventions_files,
            filing_review=filing_review,
        )
        if filing_review is not None and listing is None:
            message = "Send the complete listing for a folder review."
            raise problems.Error(
                message, code="move-input-incomplete", pointer="#/listing"
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
            conventions_files=conventions_files,
            filing_review=filing_review,
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
