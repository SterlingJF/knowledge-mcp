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
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    target_before: Path
    target_after: Path
    replacement: str | None


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
    search: list[str]
    based_on: Annotated[MoveInputs, Field(title="Move inputs")]
    writes: list[MoveWrite]
    record: str | None
    digest: Annotated[str | None, Field(pattern="^sha256:[0-9a-f]{64}$")]
    links: list[MoveLink]
    issues: list[MoveIssue]
    received: Received


type KbPrepareDocumentMoveResult = Annotated[
    DocumentMoveAnswer | problem_schema.ProblemDetails,
    Field(
        description="Replacement text and link target checks for an accepted document move, or a request for referring document text.",
        title="kb_prepare_document_move result",
    ),
]
