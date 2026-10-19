from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import importing, kbp, passages, problems
from knowledge_mcp.models import ScopeRequest
from knowledge_mcp.models_auto.import_schema import ImportAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, KnowledgeBusFolders
from knowledge_mcp.type_scope import scope_specs

DESCRIPTION = """\
Prepare an import by splitting `text` into passages and listing questions for document types in the destination `folders`. Label each passage by following the `kb-import-document` skill. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""

# Imports often share a destination folder, so `cards` caches cards by `Rebuilt.key`.
CACHED_SCOPES = 16


def register(mcp: MCPServer, workspace: Workspace) -> None:
    cards_by_scope: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}

    def cards(
        listing: dict[str, Any], rebuilt_key: str, printed: list[kbp.Printed]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Return cached cards when available, otherwise check the batch's card results.

        Raise KbpFailed when kbp fails to print a card.
        """
        if rebuilt_key in cards_by_scope:
            return cards_by_scope[rebuilt_key]
        wanted = importing.pairs(listing)

        for output in printed:
            if output.code != 0:
                raise problems.KbpFailed(output, "card")
        found = {
            pair: kbp.parsed(output, "card", kbp.CARD)
            for pair, output in zip(wanted, printed, strict=True)
        }
        if len(cards_by_scope) >= CACHED_SCOPES:
            cards_by_scope.pop(next(iter(cards_by_scope)))
        cards_by_scope[rebuilt_key] = found
        return found

    @mcp.tool(
        name="kb_prepare_import",
        title="Prepare a document import",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_prepare_import(
        location: Annotated[
            str,
            Field(
                description=(
                    "The source document's location as plain text, such as a local path, a "
                    "Drive link, a Notion page or `pasted in chat`. knowledge-mcp logs this text "
                    "and never opens the location."
                )
            ),
        ],
        text: Annotated[
            str,
            Field(
                description="The document's text, as read from its source or pasted by the person."
            ),
        ],
        folders: Annotated[
            list[str],
            Field(
                description=(
                    "Folder names from the knowledge base root folder down to the destination "
                    "folder. Empty for the root folder or when the person named no folder."
                )
            ),
        ],
        knowledge_bus_folders: KnowledgeBusFolders,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            text=text,
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
        )
        split = passages.split(text)
        if not split:
            msg = "`text` holds no passage to label. Send the document's text."
            raise problems.Error(
                msg, code="argument-invalid", pointer=problems.pointer("text")
            )
        request = ScopeRequest(
            folders=folders, knowledge_bus_folders=knowledge_bus_folders
        )
        with workspace.rebuilt(request) as rebuilt:
            listed, printed = kbp.query_scope(
                rebuilt.cwd, cards=rebuilt.key not in cards_by_scope
            )
            if listed.code != 0:
                raise problems.KbpFailed(listed, "kinds")
            listing = kbp.parsed(listed, "kinds", kbp.KINDS)
            found = cards(listing, rebuilt.key, printed)

        result = {
            "schema": importing.SCHEMA,
            "location": location,
            "universe_specs": scope_specs(listing, rebuilt),
            "document_types": importing.document_types(listing, found),
            "passages": split,
            "received": rebuilt.received,
        }
        return respond.answer(
            "kb_prepare_import", location, arguments, ImportAnswer, result
        )
