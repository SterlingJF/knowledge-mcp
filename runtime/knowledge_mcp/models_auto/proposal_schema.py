# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import problem_schema


class ProposalCell(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    label: Annotated[
        str | None,
        Field(description="The field or section, such as `Title`.", min_length=1),
    ] = None
    text: Annotated[
        str, Field(description="Plain words, without markdown syntax.", min_length=1)
    ]


type EvidenceMark = Annotated[
    Literal["supported", "partly", "conflicting", "suggested"],
    Field(
        description="How well the sources back the proposed text. `suggested` marks your own wording.",
        title="Evidence mark",
    ),
]


class LineSource(BaseModel):
    """
    A line in a text file.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[str, Field(min_length=1)]
    line_number: Annotated[int, Field(ge=1)]


class PlaceSource(BaseModel):
    """
    A place in a sheet or deck.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[str, Field(min_length=1)]
    place: Annotated[
        str, Field(description="Such as `Evening!A2:D10` or `slide 7`.", min_length=1)
    ]


class PersonSource(BaseModel):
    """
    The person's words in this conversation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    said: Annotated[str, Field(min_length=1)]


class LeftOutFile(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[str, Field(min_length=1)]
    reason: Annotated[str, Field(min_length=1)]


class ProposalRow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    current: Annotated[
        ProposalCell | None,
        Field(description="The document's text now. Omit it for an addition."),
    ] = None
    proposed: ProposalCell
    mark: EvidenceMark | None = None
    sources: Annotated[
        list[LineSource | PlaceSource | PersonSource], Field(min_length=1)
    ]


class Proposal(BaseModel):
    """
    Proposed changes to a document.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/proposal/1"], Field(alias="schema")]
    summary: Annotated[
        str, Field(description="What the proposal changes, in one line.", min_length=1)
    ]
    rows: Annotated[
        list[ProposalRow],
        Field(
            description="One row per change, in display order. The card names row n change Cn.",
            min_length=1,
        ),
    ]
    left_out: Annotated[
        list[LeftOutFile] | None, Field(description="Files you read but didn't cite.")
    ] = None
    card: Annotated[
        str,
        Field(
            description="The proposal as markdown. Show it in your reply unchanged.",
            min_length=1,
        ),
    ]


type KbPrepareProposalResult = Annotated[
    Proposal | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_prepare_proposal result, or problem details when isError is true.",
        title="kb_prepare_proposal result",
    ),
]
