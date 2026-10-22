# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import AllowedBy, Digest, EditId, EditOperation, Location, Time
from . import problem_schema


class Edit(BaseModel):
    """
    An entry from `edits.jsonl`, with legacy permission fields converted to `allowed_by`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    id: EditId
    time: Time
    location: Location
    allowed_by: AllowedBy
    whole_file: Annotated[
        Literal[True] | None,
        Field(description="Present when `before` is the whole file."),
    ] = None
    before: Annotated[
        str, Field(description="The replaced text, or an empty string for a new file.")
    ]
    before_digest: Digest
    after: Annotated[
        str | None,
        Field(
            description="Absent when the kb_record_edit call for a whole-file edit sent `after_digest` and no `after`."
        ),
    ] = None
    after_digest: Digest
    operation: EditOperation | None = None


class EditsAnswer(BaseModel):
    """
    Edits recorded for `location`, oldest first.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/edits/2"], Field(alias="schema")]
    location: Location
    edits: list[Edit]
    card: Annotated[
        str | None,
        Field(
            description="The latest edit as markdown. Absent when no edit is recorded. Show it in your reply unchanged.",
            min_length=1,
        ),
    ] = None


type KbListEditsResult = Annotated[
    EditsAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_list_edits result, or problem details when isError is true.",
        title="kb_list_edits result",
    ),
]
