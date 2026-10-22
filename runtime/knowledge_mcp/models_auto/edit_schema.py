# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import AllowedBy, Digest, EditId, EditOperation, Location, Time
from . import problem_schema


class EditReceipt(BaseModel):
    """
    The recorded edit without `before` and `after`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/edit/2"], Field(alias="schema")]
    id: EditId
    time: Time
    location: Location
    allowed_by: AllowedBy
    whole_file: Annotated[
        Literal[True] | None,
        Field(description="Present when the edit replaced the whole file."),
    ] = None
    before_digest: Digest
    after_digest: Digest
    operation: EditOperation | None = None
    card: Annotated[
        str,
        Field(
            description="The saved edit as markdown. Show it in your reply unchanged.",
            min_length=1,
        ),
    ]


type KbRecordEditResult = Annotated[
    EditReceipt | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_record_edit result, or problem details when isError is true.",
        title="kb_record_edit result",
    ),
]
