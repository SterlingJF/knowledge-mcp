from __future__ import annotations

from functools import partial
from itertools import count
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from knowledge_mcp import log, problems
from knowledge_mcp.models_auto.common_schema import Digest
from knowledge_mcp.models_auto.proposal_schema import (
    FilingNote,
    LeftOutFile,
    PersonSource,
    Proposal,
    ProposalCell,
    ProposalDocumentType,
    ProposalReader,
    ProposalRow,
)
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location
from knowledge_mcp.views import markdown

PREPARE = """\
Use whenever you propose, or are asked to review, a change to a non-code file ("review this change", "is this right"), before anything is saved. Prepare the proposed-changes card. Send each change with its sources and evidence mark, and each file you read but didn't cite. Returns the card as markdown in `card` and saves nothing. Show it unchanged unless your app already draws it, then add your own lines. Appends the answer to `log.jsonl` and opens no knowledge-base file.
"""
FIELDS = Proposal.model_fields
DOCUMENT_DIGEST = Field(
    description=(
        "The SHA-256 of the document's current text as UTF-8, written `sha256:` plus "
        "64 lowercase hex digits. Send it whenever you've read the document, so the "
        "card can refuse a save after the document changes. The answer returns it "
        "in `based_on`."
    )
)


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


def _filing_reason(filing: FilingNote | None) -> None:
    if filing is not None and filing.naming_rule is None and filing.reason is None:
        at = problems.pointer("filing", "reason")
        detail = "Say why you chose the path when no naming rule applied."
        raise problems.Error(detail, code="argument-invalid", pointer=at)


OPTIONAL = ("document_type", "reader", "filing", "open_questions", "left_out")


def register(mcp: MCPServer, workspace: Workspace) -> None:
    """Ignore `workspace`, which only keeps this signature the same as the other register() functions."""
    del workspace
    seq = count(1)

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
        document_type: Annotated[
            ProposalDocumentType | None, FIELDS["document_type"]
        ] = None,
        reader: Annotated[ProposalReader | None, FIELDS["reader"]] = None,
        filing: Annotated[FilingNote | None, FIELDS["filing"]] = None,
        open_questions: Annotated[
            list[ProposalCell] | None, FIELDS["open_questions"]
        ] = None,
        layout: Annotated[
            markdown.Layout,
            Field(
                description="`list` in a terminal, which can't scroll a wide table sideways."
            ),
        ] = "table",
        document_digest: Annotated[Digest | None, DOCUMENT_DIGEST] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            summary=summary,
            rows=rows,
            left_out=left_out,
            document_type=document_type,
            reader=reader,
            filing=filing,
            open_questions=open_questions,
            layout=layout,
            document_digest=document_digest,
        )
        _uncited(rows, left_out or [])
        _filing_reason(filing)
        data = {"schema": "knowledge-mcp/proposal/1"} | {
            name: arguments[name]
            for name in ("summary", "rows", *OPTIONAL)
            if name in arguments
        }
        if document_digest is not None:
            data["based_on"] = {"document_digest": arguments["document_digest"]}
        data["instance"] = {
            "subject": location,
            "created_at": log.now(),
            "seq": next(seq),
        }
        return respond.answer(
            "kb_prepare_proposal",
            location,
            arguments,
            Proposal,
            data,
            view=partial(markdown.proposal, layout=layout),
        )
