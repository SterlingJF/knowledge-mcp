# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from pydantic import BaseModel, ConfigDict, Field
from . import common_schema, document_types_schema, problem_schema
from typing import Annotated, Literal


class DocumentDigest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: common_schema.Path
    digest: common_schema.Digest


class MoveInputs(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    listing_digest: common_schema.Digest
    record_digest: common_schema.Digest
    documents: list[DocumentDigest]


class MoveWrite(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    old_path: common_schema.MovePath
    path: common_schema.MovePath
    before_digest: common_schema.Digest
    after_digest: common_schema.Digest
    text: str


class MoveLink(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    source_path: common_schema.MovePath
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    target_before: common_schema.Path
    target_after: common_schema.Path
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
    old_path: common_schema.MovePath
    path: common_schema.MovePath
    allowed_by: document_types_schema.AllowedBy
    search: list[str]
    based_on: Annotated[MoveInputs, Field(title="Move inputs")]
    writes: list[MoveWrite]
    record: str | None
    digest: Annotated[str | None, Field(pattern="^sha256:[0-9a-f]{64}$")]
    links: list[MoveLink]
    issues: list[MoveIssue]
    received: common_schema.Received


type KbPrepareDocumentMoveResult = Annotated[
    DocumentMoveAnswer | problem_schema.ProblemDetails,
    Field(
        description="Replacement text and link target checks for an accepted document move, or a request for referring document text.",
        title="kb_prepare_document_move result",
    ),
]
