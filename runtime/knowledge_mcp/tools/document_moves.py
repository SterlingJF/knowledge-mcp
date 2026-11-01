from __future__ import annotations

from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import document_move, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder, ListedFile
from knowledge_mcp.models_auto.common_schema import (
    DocumentMove,
    LinkBinding,
    MoveDocument,
)
from knowledge_mcp.models_auto.document_moves_schema import (
    DocumentMovesAnswer,
    MoveNaming,
    MoveStay,
)
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.document_type import RecordDigest, RecordText
from knowledge_mcp.tools.kbp import READS
from knowledge_mcp.views import markdown

DESCRIPTION = 'Use when the person asks to file, move or rename several files ("tidy my Inbox"). Prepare moves together from supplied text and a complete listing. Return search strings, affected documents and link target checks; include `allowed_by` to receive replacement text after the confirmed search. Follow `kb-write-document` to apply the moves and verify links in the saved files. Append the answer to log.jsonl and open no knowledge-base file.'

SUMMARY = "What the moves are for, in one line, such as `File the new files`. The answer echoes it."
FOLDER = "The folder the moved files come from, such as `Inbox`. The answer echoes it."
STAYS = "Files you leave where they are, each with the reason the person sees, such as `no document type` from a filing review. The answer echoes them."
NAMING = "For a move's destination `path`, the naming rule or convention that produced its name, such as `date + title`. The answer echoes them."


def _check_context(
    moves: list[DocumentMove],
    listing: list[ListedFile],
    stays: list[MoveStay],
    naming: list[MoveNaming],
) -> None:
    listed = {item.path for item in listing}
    moved = {m.old_path for m in moves}
    destinations = {m.path for m in moves}
    for index, stay in enumerate(stays):
        if stay.path not in listed:
            at = problems.pointer("stays", index, "path")
            detail = f"{stay.path} is not in the listing."
            raise problems.Error(detail, code="argument-invalid", pointer=at)
        if stay.path in moved:
            at = problems.pointer("stays", index, "path")
            detail = f"{stay.path} is moved, so it can't stay."
            raise problems.Error(detail, code="argument-invalid", pointer=at)
    for index, rule in enumerate(naming):
        if rule.path not in destinations:
            at = problems.pointer("naming", index, "path")
            detail = f"{rule.path} is not a destination in moves."
            raise problems.Error(detail, code="argument-invalid", pointer=at)


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
        summary: Annotated[str | None, Field(min_length=1, description=SUMMARY)] = None,
        folder: Annotated[str | None, Field(min_length=1, description=FOLDER)] = None,
        stays: Annotated[list[MoveStay] | None, Field(description=STAYS)] = None,
        naming: Annotated[list[MoveNaming] | None, Field(description=NAMING)] = None,
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
            summary=summary,
            folder=folder,
            stays=stays,
            naming=naming,
        )
        _check_context(moves, listing, stays or [], naming or [])
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
        for name in ("summary", "folder", "stays", "naming"):
            if name in arguments:
                result[name] = arguments[name]
        document_move.check_batch_size(result)
        return respond.answer(
            "kb_prepare_document_moves",
            location,
            arguments,
            DocumentMovesAnswer,
            result,
            view=markdown.moves,
        )
