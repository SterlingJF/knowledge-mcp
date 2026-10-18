from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import conventions as patterns
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder
from knowledge_mcp.models_auto.common_schema import ConventionFile
from knowledge_mcp.models_auto.conventions_schema import ConventionReference
from knowledge_mcp.models_auto.conventions_update_schema import (
    Change,
    ConventionsUpdateAnswer,
)
from knowledge_mcp.models_auto.folder_conventions_schema import FolderConventionsAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location
from knowledge_mcp.type_scope import Scopes

ConventionsText = Annotated[
    str | None,
    Field(
        description="Current target conventions file text. Send empty text when the file is absent."
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
        name="kb_list_conventions",
        title="List folder conventions",
        description="List naming and filing conventions that apply in a folder, with their source folders and parent marks. Report inactive declarations. Append the answer to log.jsonl and open no knowledge-base file.",
        annotations=READS,
    )
    def kb_list_conventions(
        location: Location,
        folder: str,
        knowledge_bus_folders: list[KnowledgeBusFolder],
        conventions_files: list[ConventionFile],
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            folder=folder,
            knowledge_bus_folders=knowledge_bus_folders,
            conventions_files=conventions_files,
        )
        scopes = Scopes(workspace, knowledge_bus_folders)
        context = patterns.Context(workspace, scopes, conventions_files)
        result = context.inspect(folder)
        return respond.answer(
            "kb_list_conventions",
            location,
            arguments,
            FolderConventionsAnswer,
            dict(
                schema="knowledge-mcp/folder-conventions/1",
                location=location,
                folder=folder,
                **result,
                received=[*scopes.received.values(), *context.received.values()],
            ),
        )

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
        folder: str = "",
        conventions_files: list[ConventionFile] | None = None,
        from_parent: list[ConventionReference] | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            conventions=conventions,
            conventions_digest=conventions_digest,
            knowledge_bus_folders=knowledge_bus_folders,
            changes=changes,
            allowed_by=allowed_by,
            folder=folder,
            conventions_files=conventions_files,
            from_parent=from_parent,
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
                    target=patterns.Target(
                        knowledge_bus_folders,
                        folder,
                        conventions_files,
                        [patterns.plain(r) for r in from_parent]
                        if from_parent is not None
                        else None,
                    ),
                ),
            },
        )
