# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import common_schema, document_types_schema, problem_schema


class EditReceipt(BaseModel):
    """
    The recorded edit without `before` and `after`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/edit/1"], Field(alias="schema")]
    id: common_schema.EditId
    time: common_schema.Time
    location: common_schema.Location
    allowed_by: document_types_schema.AllowedBy
    whole_file: Annotated[
        Literal[True] | None,
        Field(description="Present when the edit replaced the whole file."),
    ] = None
    before_digest: common_schema.Digest
    after_digest: common_schema.Digest


type KbRecordEditResult = Annotated[
    EditReceipt | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_record_edit result, or problem details when isError is true.",
        title="kb_record_edit result",
    ),
]
