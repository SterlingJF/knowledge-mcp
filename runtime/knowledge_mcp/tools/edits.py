"""`kb_record_edit` and `kb_edits`: the agent's record of each edit, for checking and undo."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from knowledge_mcp import edits
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Location

RECORD = """\
Record an edit you made to a document, right after making the edit, so the person can check \
and undo the edit. Send the location text, the basis and its text, the text before the edit and \
the text after the edit. `basis` says why you edited: `request` for a request the person made in this \
session, `line` for a standing line the person wrote, such as one in AGENTS.md, or \
`change_row` for a change row the person accepted. `basis_text` quotes the request, line or \
row; `basis_location` says where a line or row sits. `before` is the text the edit replaced, \
the whole file or the passage, and empty for a new file; `after` is the text that replaced \
`before`. Set `whole_file` when `before` is the whole file; only then can `after_digest` stand \
in for `after`. knowledge-mcp appends the record to its own state folder and changes no file \
of the knowledge base.\
"""

LIST = """\
List every edit recorded at a location, oldest first, with its basis and its texts. To undo an \
edit, check that the document still holds the edit's `after` text, then put the `before` text \
back in its place. For an edit with `whole_file` and no `after`, check that the whole file \
matches `after_digest`, then write `before` as the whole file.\
"""


def register(mcp: Any, workspace: Any) -> None:
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
        basis: Annotated[
            edits.Basis,
            Field(
                description=(
                    "`request`, `line` or `change_row`: what the person said that let you edit."
                )
            ),
        ],
        basis_text: Annotated[
            str, Field(description="The request, line or change row, quoted.")
        ],
        before: Annotated[
            str,
            Field(description="The text the edit replaced; empty for a new file."),
        ],
        after: Annotated[
            str | None, Field(description="The text that replaced `before`.")
        ] = None,
        after_digest: Annotated[
            str | None,
            Field(
                description=(
                    "`sha256:` and the 64 lowercase hex digits of the SHA-256 of `after` as "
                    "UTF-8; stands in for `after` only with `whole_file`."
                )
            ),
        ] = None,
        whole_file: Annotated[
            bool | None,
            Field(description="True when `before` is the whole file."),
        ] = None,
        basis_location: Annotated[
            str | None,
            Field(
                description="The file or place holding the line or change row, such as `AGENTS.md`."
            ),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            basis=basis,
            basis_text=basis_text,
            before=before,
            after=after,
            after_digest=after_digest,
            whole_file=whole_file,
            basis_location=basis_location,
        )
        try:
            entry = edits.record(
                location=location,
                basis=basis,
                basis_text=basis_text,
                basis_location=basis_location,
                before=before,
                after=after,
                after_digest=after_digest,
                whole_file=bool(whole_file),
            )
        except edits.EditError as error:
            return respond.refusal("kb_record_edit", location, arguments, str(error))
        text = respond.compact(edits.receipt(entry))
        return respond.answer(
            "kb_record_edit", location, arguments, [TextContent(type="text", text=text)]
        )

    @mcp.tool(
        name="kb_edits",
        title="List recorded edits",
        description=LIST,
        annotations=READS,
    )
    def kb_edits(location: Location) -> CallToolResult:
        arguments = respond.sent(location=location)
        text = respond.compact(edits.listing(location))
        return respond.answer(
            "kb_edits", location, arguments, [TextContent(type="text", text=text)]
        )
