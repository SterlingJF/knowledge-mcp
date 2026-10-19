# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from pydantic import BaseModel, ConfigDict, Field
from ._internal import AllowedBy, Digest, MovePath, Path, Received
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


class MoveIssue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    code: str
    source_path: str | None
    start: Annotated[int | None, Field(ge=0)]
    end: Annotated[int | None, Field(ge=0)]
    detail: str


class DocumentMoveAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/document-move/1"], Field(alias="schema")]
    location: str
    status: Literal["texts_needed", "ready", "blocked", "unchanged"]
    old_path: MovePath
    path: MovePath
    allowed_by: AllowedBy
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


type KbPrepareDocumentMoveResult = Annotated[
    DocumentMoveAnswer | problem_schema.ProblemDetails,
    Field(
        description="Prepared replacement text and link target checks against supplied inputs for an accepted document move, or a request for referring document text. The agent applies the move and verifies the saved files.",
        title="kb_prepare_document_move result",
    ),
]
