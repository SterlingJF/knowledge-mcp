from __future__ import annotations

from typing import Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult

from knowledge_mcp import document_move
from knowledge_mcp import document_types as records
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder, ListedFile
from knowledge_mcp.models_auto.common_schema import (
    DocumentMove,
    LinkBinding,
    MoveDocument,
)
from knowledge_mcp.models_auto.document_moves_schema import DocumentMovesAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.document_type import RecordDigest, RecordText
from knowledge_mcp.tools.kbp import READS

DESCRIPTION = "Prepare moves together from supplied text and a complete listing. Return search strings, affected documents and replacement text while preserving link targets. Append the answer to log.jsonl and open no knowledge-base file."


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_prepare_document_moves",
        title="Prepare document moves",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_prepare_document_moves(
        location: str,
        moves: list[DocumentMove],
        listing: list[ListedFile],
        documents: list[MoveDocument],
        case_mode: Literal["sensitive", "insensitive"],
        knowledge_bus_folders: list[KnowledgeBusFolder],
        record: RecordText = None,
        record_digest: RecordDigest = None,
        allowed_by: AllowedBy | None = None,
        searched: bool = False,
        search: list[str] | None = None,
        bindings: list[LinkBinding] | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            moves=moves,
            listing=listing,
            documents=documents,
            case_mode=case_mode,
            knowledge_bus_folders=knowledge_bus_folders,
            record=record,
            record_digest=record_digest,
            allowed_by=allowed_by,
            searched=searched,
            search=search,
            bindings=bindings,
        )
        text = records.received_text(record, record_digest, workspace.recall)
        sent = document_move.BatchRequest(
            location,
            moves,
            listing,
            documents,
            case_mode,
            bindings or [],
            searched,
            search or [],
            allowed_by,
            knowledge_bus_folders,
        )
        result = document_move.prepare_batch(workspace, sent, text)
        if record is not None:
            result["received"].append(
                dict(name=records.PLACE, digest=workspace.remember(text))
            )
        document_move.check_batch_size(result)
        return respond.answer(
            "kb_prepare_document_moves",
            location,
            arguments,
            DocumentMovesAnswer,
            result,
        )
