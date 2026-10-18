# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import common_schema, problem_schema


class AudienceFrame(BaseModel):
    """
    The audience question from the universe spec, or null when the universe spec has none.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    id: Literal["audience"]
    question: str


class AudienceChoice(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[str, Field(min_length=1)]
    label: str
    question: Annotated[
        str | None,
        Field(description="The question for this choice, from the universe spec."),
    ] = None


class AudiencesAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/audiences/1"], Field(alias="schema")]
    location: common_schema.Location
    universe_spec: Annotated[
        str,
        Field(
            description="The id of the universe spec that holds the document type.",
            min_length=1,
        ),
    ]
    universe_specs: Annotated[
        list[common_schema.SpecInScope],
        Field(
            description="The universe spec named by `universe_spec`.",
            max_length=1,
            min_length=1,
        ),
    ]
    document_type: Annotated[str, Field(min_length=1)]
    actor: Annotated[
        str | None,
        Field(description="The role that uses the document type, from kbp_kinds."),
    ]
    frame: Annotated[
        AudienceFrame | None,
        Field(
            description="The audience question from the universe spec, or null when the universe spec has none.",
            title="Audience frame",
        ),
    ]
    choices: Annotated[
        list[AudienceChoice], Field(description="In universe spec order.")
    ]
    received: common_schema.Received


type KbListAudiencesResult = Annotated[
    AudiencesAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_list_audiences result, or problem details when isError is true.",
        title="kb_list_audiences result",
    ),
]
