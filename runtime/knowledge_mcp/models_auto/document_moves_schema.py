# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from pydantic import BaseModel, ConfigDict, Field
from ._internal import AllowedBy, Digest, DocumentMove, MovePath, Path, Received
from typing import Annotated, Literal
from . import problem_schema


class DocumentDigest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    digest: Digest


class MoveInputs(BaseModel):
    """
    Input digests for the agent to recheck before applying writes.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    listing_digest: Digest
    record_digest: Digest
    documents: list[DocumentDigest]
    configuration: Received


class MoveWrite(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    old_path: MovePath
    path: MovePath
    before_digest: Digest
    after_digest: Digest
    text: str


class MoveLink(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    source_path: MovePath
    start: Annotated[
        int,
        Field(
            description="Zero-based Unicode code-point offset of the complete link token in the original supplied text.",
            ge=0,
        ),
    ]
    end: Annotated[
        int,
        Field(
            description="Exclusive Unicode code-point offset after the complete original link token.",
            ge=0,
        ),
    ]
    target_before: Path
    target_after: Path
    replacement: Annotated[
        str | None,
        Field(
            description="The complete replacement link token, or null when the original token needs no change."
        ),
    ]


class MoveStay(BaseModel):
    """
    A file the assistant leaves where it is, with the reason the person sees.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    path: MovePath
    reason: Annotated[
        str,
        Field(
            description="Why the file stays, such as `no document type`.", min_length=1
        ),
    ]


class MoveNaming(BaseModel):
    """
    The naming rule or convention that produced a move's destination name.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    path: Annotated[
        MovePath, Field(description="The destination `path` of one move in `moves`.")
    ]
    rule: Annotated[
        str,
        Field(
            description="The rule in a few words, such as `date + title`.", min_length=1
        ),
    ]


class MoveIssueChoice(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    action: Annotated[
        Literal["skip_move", "bind_link"],
        Field(
            description="`skip_move` drops the move of `path` from `moves`. `bind_link` sends a binding for the issue's link with `path` as its target."
        ),
    ]
    path: MovePath


class MoveIssue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    code: str
    source_path: str | None
    start: Annotated[int | None, Field(ge=0)]
    end: Annotated[int | None, Field(ge=0)]
    detail: str
    choices: Annotated[
        list[MoveIssueChoice] | None,
        Field(
            description="Resolutions the server can compute for this issue. Absent when it can compute none.",
            min_length=1,
        ),
    ] = None


class DocumentMovesAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/document-moves/1"], Field(alias="schema")]
    location: str
    status: Literal[
        "texts_needed", "permission_needed", "ready", "blocked", "unchanged"
    ]
    allowed_by: AllowedBy | None
    search: Annotated[
        list[str],
        Field(
            description="Fixed strings to search case-insensitively across Markdown files; echo the complete array after searching."
        ),
    ]
    based_on: Annotated[
        MoveInputs,
        Field(
            description="Input digests for the agent to recheck before applying writes.",
            title="Move inputs",
        ),
    ]
    writes: Annotated[
        list[MoveWrite],
        Field(
            description="Prepared document replacements for the agent to apply as one operation with `record`."
        ),
    ]
    record: Annotated[
        str | None,
        Field(
            description="Prepared document-types text for the agent to save with the document writes, or null when no writes are prepared."
        ),
    ]
    digest: Annotated[str | None, Field(pattern="^sha256:[0-9a-f]{64}$")]
    links: list[MoveLink]
    issues: list[MoveIssue]
    received: Received
    moves: list[DocumentMove]
    affected_documents: list[DocumentMove]
    record_changes: list[DocumentMove]
    summary: Annotated[
        str | None,
        Field(
            description="What the moves are for, in one line, echoed from the `summary` argument.",
            min_length=1,
        ),
    ] = None
    folder: Annotated[
        str | None,
        Field(
            description="The folder the moved files come from, echoed from the `folder` argument.",
            min_length=1,
        ),
    ] = None
    stays: Annotated[
        list[MoveStay] | None,
        Field(
            description="Files left where they are, with reasons, echoed from the `stays` argument."
        ),
    ] = None
    naming: Annotated[
        list[MoveNaming] | None,
        Field(
            description="The naming rule behind each named destination, echoed from the `naming` argument."
        ),
    ] = None
    card: Annotated[
        str | None,
        Field(
            description="The move plan as markdown. Show it in your reply unchanged.",
            min_length=1,
        ),
    ] = None


type KbPrepareDocumentMovesResult = Annotated[
    DocumentMovesAnswer | problem_schema.ProblemDetails,
    Field(
        description="Prepared replacement text and link target checks against supplied inputs for moves prepared together. The agent applies the moves and verifies the saved files.",
        title="kb_prepare_document_moves result",
    ),
]
