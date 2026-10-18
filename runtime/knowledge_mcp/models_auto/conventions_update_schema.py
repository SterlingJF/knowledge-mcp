# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import (
    AllowedBy,
    ConventionContent,
    ConventionName,
    ConventionReference,
    ConventionSegment,
    ConventionsFolder,
    Digest,
    Location,
    Part,
    Received,
    SavedConvention,
    SetBy,
)
from . import problem_schema


class RemoveConvention(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["remove"]
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]


class UpsertConvention(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["upsert"]
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    folder: list[ConventionSegment | Part]
    name: ConventionName
    content: ConventionContent | None = None
    set_by: SetBy


type Change = Annotated[
    UpsertConvention | RemoveConvention, Field(title="Convention change")
]


class ConventionsUpdateAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[
        Literal["knowledge-mcp/conventions-update/1"], Field(alias="schema")
    ]
    location: Location
    folder: ConventionsFolder | None = None
    current_from_parent: list[ConventionReference] | None = None
    proposed_from_parent: list[ConventionReference] | None = None
    file: Literal[".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"]
    status: Literal["ready", "permission_needed", "unchanged"]
    based_on: Digest
    current: list[SavedConvention]
    changes: list[Change]
    allowed_by: AllowedBy | None
    record: str | None
    digest: Digest | None
    received: Received


type KbPrepareConventionsResult = Annotated[
    ConventionsUpdateAnswer | problem_schema.ProblemDetails,
    Field(
        description="Prepared conventions text or problem details.",
        title="kb_prepare_conventions result",
    ),
]
