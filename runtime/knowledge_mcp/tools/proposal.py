from __future__ import annotations

from functools import partial
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import problems
from knowledge_mcp.models_auto.proposal_schema import (
    LeftOutFile,
    PersonSource,
    Proposal,
    ProposalRow,
)
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location
from knowledge_mcp.views import markdown

PREPARE = """\
Prepare the proposed-changes card whenever you propose changes to a document, before any edit. Send each change as a row with its sources and evidence mark, and each file you read but didn't cite. Returns the card as markdown in `card` and saves nothing. Show `card` in your reply unchanged, then add your own lines. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""
FIELDS = Proposal.model_fields


def _uncited(rows: list[ProposalRow], left_out: list[LeftOutFile]) -> None:
    cited = {
        source.file
        for row in rows
        for source in row.sources
        if not isinstance(source, PersonSource)
    }
    for index, left in enumerate(left_out):
        if left.file in cited:
            at = problems.pointer("left_out", index, "file")
            detail = f"{left.file} is cited in a row."
            raise problems.Error(detail, code="argument-invalid", pointer=at)


def register(mcp: MCPServer, workspace: Workspace) -> None:
    """Ignore `workspace`, which only keeps this signature the same as the other register() functions."""
    del workspace

    @mcp.tool(
        name="kb_prepare_proposal",
        title="Prepare a proposal card",
        description=PREPARE,
        annotations=READS,
    )
    def kb_prepare_proposal(
        location: Location,
        summary: Annotated[str, FIELDS["summary"]],
        rows: Annotated[list[ProposalRow], FIELDS["rows"]],
        left_out: Annotated[list[LeftOutFile] | None, FIELDS["left_out"]] = None,
        layout: Annotated[
            markdown.Layout,
            Field(
                description="`list` in a terminal, which can't scroll a wide table sideways."
            ),
        ] = "table",
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            summary=summary,
            rows=rows,
            left_out=left_out,
            layout=layout,
        )
        _uncited(rows, left_out or [])
        data = {"schema": "knowledge-mcp/proposal/1"} | {
            name: arguments[name]
            for name in ("summary", "rows", "left_out")
            if name in arguments
        }
        return respond.answer(
            "kb_prepare_proposal",
            location,
            arguments,
            Proposal,
            data,
            view=partial(markdown.proposal, layout=layout),
        )
