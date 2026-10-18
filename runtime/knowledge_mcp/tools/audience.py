from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import audience, kbp, problems
from knowledge_mcp.models import ScopeRequest
from knowledge_mcp.models_auto.audiences_schema import AudiencesAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Folders, KnowledgeBusFolders, Location
from knowledge_mcp.type_scope import scope_specs

DESCRIPTION = """\
List the readers you can choose for a document type. Returns the document type's `actor`, plus the audience question and its `choices` from the universe spec. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""

UniverseSpec = Annotated[
    str | None,
    Field(
        description=(
            "Id of the universe spec to use when the document type appears in more than one "
            "universe spec that applies."
        )
    ),
]


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_list_audiences",
        title="List reader choices",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_list_audiences(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        document_type: Annotated[
            str, Field(description="A document type id, such as `design-doc`.")
        ],
        universe_spec: UniverseSpec = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            document_type=document_type,
            universe_spec=universe_spec,
        )
        request = ScopeRequest(
            folders=folders, knowledge_bus_folders=knowledge_bus_folders
        )
        with workspace.rebuilt(request) as rebuilt:
            listed = kbp.run(["--kinds"], rebuilt.cwd)
            if listed.code != 0:
                raise problems.KbpFailed(listed, "kinds")
            listing = kbp.parsed(listed, "kinds", kbp.KINDS)
            spec, item = audience.holder(listing, document_type, universe_spec)
            inspected = kbp.run(["--inspect", "--universe", spec["id"]], rebuilt.cwd)
            if inspected.code != 0:
                raise problems.KbpFailed(inspected, "inspect")
            model = kbp.parsed(inspected, "inspect", kbp.EXPLORER_MODEL)
            declared, choices = audience.frame(model)

        result = {
            "schema": audience.SCHEMA,
            "location": location,
            "universe_spec": spec["id"],
            "universe_specs": [
                found
                for found in scope_specs(listing, rebuilt)
                if found["id"] == spec["id"]
            ],
            "document_type": document_type,
            "actor": item["actor"],
            "frame": declared,
            "choices": choices,
            "received": rebuilt.received,
        }
        return respond.answer(
            "kb_list_audiences", location, arguments, AudiencesAnswer, result
        )
