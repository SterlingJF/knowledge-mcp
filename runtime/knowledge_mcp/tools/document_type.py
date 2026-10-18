from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import document_type, kbp, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.models import FileChange, KnowledgeBusFolder, ScopeRequest
from knowledge_mcp.models_auto.common_schema import Digest
from knowledge_mcp.models_auto.document_type_schema import DocumentTypeAnswer
from knowledge_mcp.scope import SENT, Rebuilt, Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Folders, KnowledgeBusFolders, Location

DESCRIPTION = """\
Get a file's document type before writing or editing. Returns an applicable saved entry from `record` or `record_digest`, or ranked candidates plus every document type when no candidate matches the file name. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""


RecordText = Annotated[
    str | None,
    Field(
        description=(
            f"The unedited text of `{records.PLACE}` under the knowledge base root folder. "
            f"When that file is missing, send the text of `{records.OLD_PLACE}`, which "
            "knowledge-mcp 0.2.1 and earlier used. Send an empty string when both files are "
            "missing."
        ),
    ),
]
RecordDigest = Annotated[
    Digest | None,
    Field(
        description=(
            "Send the document-types digest from an earlier result in this session "
            "in place of `record` while the file remains unchanged."
        )
    ),
]
Role = Annotated[str | None, Field(description=document_type.ROLE)]
Changes = Annotated[
    list[FileChange] | None,
    Field(
        description=(
            "Files changed since the document-types file was last saved. Send them with "
            "`record` or `record_digest`. knowledge-mcp applies the changes to the entries "
            "for this answer only."
        )
    ),
]


def kinds_of(listing: dict[str, Any]) -> records.Kinds:
    return {
        group["universe_spec"]["id"]: (
            str(group["universe_spec"]["version"]),
            frozenset(kind["kind"] for kind in group["kinds"]),
        )
        for group in listing.get("universe_specs", [listing])
    }


def scope_specs(listing: dict[str, Any], rebuilt: Rebuilt) -> list[dict[str, Any]]:
    groups = listing.get("universe_specs", [listing])
    parents = set(listing.get("from_parent", []))
    return [
        {
            "id": spec["id"],
            "version": spec["version"],
            "source": rebuilt.sources.get(spec["id"], SENT),
            "from_parent": spec["id"] in parents
            or (rebuilt.nearest is not None and spec["id"] not in rebuilt.nearest),
        }
        for spec in (group["universe_spec"] for group in groups)
    ]


def listed_kinds(
    workspace: Workspace, request: ScopeRequest
) -> tuple[dict[str, Any], Rebuilt]:
    """Raise KbpFailed when kbp exits nonzero."""
    with workspace.rebuilt(request) as rebuilt:
        output = kbp.run(["--kinds"], rebuilt.cwd)
    if output.code != 0:
        raise problems.KbpFailed(output, "kinds")
    return kbp.parsed(output, "kinds", kbp.KINDS), rebuilt


def _saved_files(
    workspace: Workspace,
    record: str | None,
    record_digest: str | None,
    changes: list[FileChange] | None,
    received: list[dict[str, Any]],
) -> records.Files | None:
    """Append the digest of `record` to `received` when `record` is set.
    Raise DocumentTypesError when `changes` is nonempty and both `record` and `record_digest` are None.
    """
    if changes and record is None and record_digest is None:
        msg = "Send `record` or `record_digest` with `changes`."
        raise records.DocumentTypesError(msg, pointer=problems.pointer("changes"))
    if record is None and record_digest is None:
        return None
    text = records.received_text(record, record_digest, workspace.recall)
    files = records.parse(text)
    if record is not None:
        received.append({"name": records.PLACE, "digest": workspace.remember(text)})
    return files


def get_document_type(
    workspace: Workspace,
    *,
    location: str,
    name: str,
    folders: list[str],
    knowledge_bus_folders: list[KnowledgeBusFolder],
    role: str | None,
    record: str | None,
    record_digest: str | None,
    changes: list[FileChange] | None,
) -> dict[str, Any]:
    received: list[dict[str, Any]] = []
    files = _saved_files(workspace, record, record_digest, changes, received)
    listing, rebuilt = listed_kinds(
        workspace,
        ScopeRequest(folders=folders, knowledge_bus_folders=knowledge_bus_folders),
    )
    specs = scope_specs(listing, rebuilt)
    if files is not None and changes:
        # records.lookup reads only the requested file's entry, so a wrong document-type list
        # for the other changed paths does no harm.
        kinds = kinds_of(listing)
        files = records.merge(
            files,
            records.MergeRequest(
                events=[records.event(change) for change in changes],
                entries=[],
                recheck=False,
                kinds_at=lambda _path: kinds,
                allowed_by=None,
                fingerprints={},
            ),
        ).files
    entry = None
    key = ""
    if files is not None:
        key, entry = records.lookup(files, folders, name)
        in_scope = {spec["id"] for spec in specs}
        universe_spec, _, untyped = (
            records.named(entry) if entry else (None, None, False)
        )
        if entry is not None and not (untyped or universe_spec in in_scope):
            entry = None
    if entry is not None:
        result: dict[str, Any] = {
            "schema": document_type.SCHEMA,
            "location": location,
            "universe_specs": specs,
            "candidates": [],
            "every_document_type": None,
            "recorded": records.answer(key, entry),
        }
    else:
        result = document_type.answer(
            listing,
            document_type.MatchRequest(
                location=location,
                name=name,
                folders=folders,
                role=role,
                universe_specs=specs,
            ),
        )
    result["received"] = rebuilt.received + received
    return result


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_get_document_type",
        title="Get the document type",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_get_document_type(
        location: Location,
        name: str,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        role: Role = None,
        record: RecordText = None,
        record_digest: RecordDigest = None,
        changes: Changes = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            name=name,
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            role=role,
            record=record,
            record_digest=record_digest,
            changes=changes,
        )
        result = get_document_type(
            workspace,
            location=location,
            name=name,
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            role=role,
            record=record,
            record_digest=record_digest,
            changes=changes,
        )
        return respond.answer(
            "kb_get_document_type", location, arguments, DocumentTypeAnswer, result
        )
