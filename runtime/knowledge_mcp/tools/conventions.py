from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import conventions as patterns
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder
from knowledge_mcp.models_auto.conventions_update_schema import (
    Change,
    ConventionsUpdateAnswer,
)
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location

ConventionsText = Annotated[
    str | None,
    Field(
        description="Current root conventions file text. Send empty text when the file is absent."
    ),
]
ConventionsDigest = Annotated[
    str | None,
    Field(
        description="Conventions digest received in this session. Reuse while the file remains unchanged."
    ),
]


def register(mcp: MCPServer, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_prepare_conventions",
        title="Prepare naming and filing conventions",
        description="Prepare conventions text from supplied configuration and proposed changes. Include permission to receive replacement text. Append the answer to log.jsonl and open no knowledge-base file.",
        annotations=READS,
    )
    def kb_prepare_conventions(
        location: Location,
        conventions: ConventionsText = None,
        conventions_digest: ConventionsDigest = None,
        knowledge_bus_folders: list[KnowledgeBusFolder] = [],  # noqa: B006 - Pydantic copies defaults.
        changes: list[Change] = [],  # noqa: B006 - Pydantic copies defaults.
        allowed_by: AllowedBy | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            conventions=conventions,
            conventions_digest=conventions_digest,
            knowledge_bus_folders=knowledge_bus_folders,
            changes=changes,
            allowed_by=allowed_by,
        )
        return respond.answer(
            "kb_prepare_conventions",
            location,
            arguments,
            ConventionsUpdateAnswer,
            {
                "location": location,
                **patterns.prepare(
                    workspace,
                    patterns.received_text(workspace, conventions, conventions_digest),
                    changes=changes,
                    allowed_by=allowed_by,
                    folders=knowledge_bus_folders,
                ),
            },
        )
