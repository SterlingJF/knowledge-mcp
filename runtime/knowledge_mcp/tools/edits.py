from __future__ import annotations

from typing import Annotated

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from knowledge_mcp import edits
from knowledge_mcp.models import AllowedBy
from knowledge_mcp.models_auto.common_schema import EditOperation
from knowledge_mcp.models_auto.edit_schema import EditReceipt
from knowledge_mcp.models_auto.edits_schema import EditsAnswer
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location

RECORD = """\
Record an edit right after you make it, so the person can check or undo the change. Returns the edit's id and the digests of `before` and `after`. Appends the edit to `edits.jsonl` and the answer to `log.jsonl`, and opens no knowledge-base file.
"""

LIST = """\
List the edits recorded for `location`, oldest first, to check or undo an edit. The `kb-write-document` skill gives the undo steps. Reads `edits.jsonl`, appends the answer to `log.jsonl`, and opens no knowledge-base file.
"""


def register(mcp: MCPServer, workspace: Workspace) -> None:
    """Ignore `workspace`, which only keeps this signature the same as the other register() functions."""
    del workspace

    @mcp.tool(
        name="kb_record_edit",
        title="Record an edit",
        description=RECORD,
        annotations=ToolAnnotations(
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    def kb_record_edit(
        location: Location,
        allowed_by: AllowedBy,
        before: Annotated[
            str,
            Field(
                description="The replaced text. Send an empty string for a new file."
            ),
        ],
        after: Annotated[
            str | None,
            Field(
                description=(
                    "The text that replaced `before`. Omit it only for a whole-file edit sent "
                    "with `after_digest`."
                )
            ),
        ] = None,
        after_digest: Annotated[
            str | None,
            Field(
                description=(
                    "The SHA-256 of `after` as UTF-8, written `sha256:` plus 64 lowercase hex "
                    "digits. Replaces `after` only when `whole_file` is true."
                )
            ),
        ] = None,
        whole_file: Annotated[
            bool | None,
            Field(description="True when `before` is the whole file."),
        ] = None,
        operation: EditOperation | None = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            allowed_by=allowed_by,
            before=before,
            after=after,
            after_digest=after_digest,
            whole_file=whole_file,
            operation=operation,
        )
        texts = edits.Texts(
            before=before,
            after=after,
            after_digest=after_digest,
            whole_file=bool(whole_file),
        )
        entry = edits.record(location, allowed_by, texts, operation)
        return respond.answer(
            "kb_record_edit", location, arguments, EditReceipt, edits.receipt(entry)
        )

    @mcp.tool(
        name="kb_list_edits",
        title="List recorded edits",
        description=LIST,
        annotations=READS,
    )
    def kb_list_edits(location: Location) -> CallToolResult:
        arguments = respond.sent(location=location)
        return respond.answer(
            "kb_list_edits", location, arguments, EditsAnswer, edits.listing(location)
        )
