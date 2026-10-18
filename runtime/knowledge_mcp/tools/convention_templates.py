from __future__ import annotations

from mcp.server import MCPServer
from mcp.types import CallToolResult

from knowledge_mcp import convention_templates
from knowledge_mcp.models_auto.convention_templates_schema import (
    ConventionTemplatesAnswer,
)
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location


def register(mcp: MCPServer) -> None:
    @mcp.tool(
        name="kb_list_convention_templates",
        title="List convention templates",
        description="List bundled ACE, PARA and Johnny.Decimal definitions for notes, with folder purposes, naming suggestions and sources. Append the answer to log.jsonl.",
        annotations=READS,
    )
    def kb_list_convention_templates(location: Location) -> CallToolResult:
        return respond.answer(
            "kb_list_convention_templates",
            location,
            respond.sent(location=location),
            ConventionTemplatesAnswer,
            convention_templates.catalog(location),
        )
