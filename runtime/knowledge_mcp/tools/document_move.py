from __future__ import annotations

from typing import Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult

from knowledge_mcp import document_move
from knowledge_mcp import document_types as records
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder, ListedFile
from knowledge_mcp.models_auto.common_schema import LinkBinding, MoveDocument, MovePath
from knowledge_mcp.models_auto.document_move_schema import DocumentMoveAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.document_type import RecordDigest, RecordText
from knowledge_mcp.tools.kbp import READS

DESCRIPTION = "Prepare a document move from supplied text, a complete listing and permission. Return search strings for referring documents, then replacement text and link target checks after the confirmed search. Follow `kb-write-document` to apply the move and verify links in the saved files. Append the answer to log.jsonl and open no knowledge-base file."


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_prepare_document_move",
        title="Prepare a document move",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_prepare_document_move(
        location: str,
        old_path: MovePath,
        path: MovePath,
        listing: list[ListedFile],
        documents: list[MoveDocument],
        case_mode: Literal["sensitive", "insensitive"],
        allowed_by: AllowedBy,
        knowledge_bus_folders: list[KnowledgeBusFolder],
        record: RecordText = None,
        record_digest: RecordDigest = None,
        searched: bool = False,
        search: list[str] | None = None,
        bindings: list[LinkBinding] | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            old_path=old_path,
            path=path,
            listing=listing,
            documents=documents,
            case_mode=case_mode,
            allowed_by=allowed_by,
            knowledge_bus_folders=knowledge_bus_folders,
            record=record,
            record_digest=record_digest,
            searched=searched,
            search=search,
            bindings=bindings,
        )
        text = records.received_text(record, record_digest, workspace.recall)
        request = document_move.Request(
            location,
            old_path,
            path,
            listing,
            documents,
            case_mode,
            bindings or [],
            searched,
            search or [],
            allowed_by,
            knowledge_bus_folders,
        )
        result = document_move.prepare(workspace, request, text)
        if record is not None:
            result["received"].append(
                dict(name=records.PLACE, digest=workspace.remember(text))
            )
        return respond.answer(
            "kb_prepare_document_move", location, arguments, DocumentMoveAnswer, result
        )
