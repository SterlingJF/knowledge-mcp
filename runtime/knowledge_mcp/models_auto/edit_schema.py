# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import AllowedBy, Digest, EditId, EditOperation, Location, Time
from . import problem_schema


class ChangedLine(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["removed", "added"]
    text: Annotated[str, Field(description="The line without its line ending.")]


class UndoneEdit(BaseModel):
    """
    The earlier edit this edit undoes, named by the `undoes` argument.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    id: EditId
    time: Time


class EditChanges(BaseModel):
    """
    The changed lines of an edit in document order, capped at 12 lines. Absent when the edit sent `after_digest` without `after`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    hunks: Annotated[
        int, Field(description="The number of separate changed blocks.", ge=0)
    ]
    lines: Annotated[list[ChangedLine], Field(max_length=12)]
    more: Annotated[
        int, Field(description="The number of changed lines beyond the cap.", ge=0)
    ]


class EditReceipt(BaseModel):
    """
    The recorded edit without `before` and `after`, which the agent already has. `changes` carries a capped excerpt of the changed lines instead.
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
    created: Annotated[
        Literal[True] | None,
        Field(
            description="Present when the edit created the file, that is when `before` was empty."
        ),
    ] = None
    undoes: Annotated[
        UndoneEdit | None,
        Field(
            description="The earlier edit this edit undoes, named by the `undoes` argument.",
            title="Undone edit",
        ),
    ] = None
    changes: EditChanges | None = None
    card: Annotated[
        str,
        Field(
            description="The saved edit as markdown. Show it in your reply unchanged, unless your app already draws it as a card.",
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
