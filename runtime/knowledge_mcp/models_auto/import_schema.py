# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import Location, Received, SpecInScope
from . import problem_schema


class ElementQuestion(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    element: Annotated[str, Field(min_length=1)]
    question: Annotated[str, Field(min_length=1)]
    strength: Annotated[
        str, Field(description="`core` or `situational`, from the card.")
    ]


class ImportDocumentType(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    name: str
    action: Annotated[str | None, Field(description="From kbp_kinds.")]
    actor: Annotated[
        str | None,
        Field(description="The role that uses the document type, from kbp_kinds."),
    ]
    elements: Annotated[
        list[ElementQuestion],
        Field(
            description="Sections of the document type's card, in card order, without `links` sections."
        ),
    ]


type Line = Annotated[int, Field(ge=1)]


class Passage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[str, Field(pattern="^p[1-9][0-9]*$")]
    kind: Literal["heading", "paragraph", "list-item", "code"]
    lines: Annotated[
        list[Line],
        Field(
            description="Inclusive first and last line numbers in the source text, starting at one.",
            max_length=2,
            min_length=2,
        ),
    ]
    opening: Annotated[
        str,
        Field(
            description="The passage's first line with spaces collapsed. knowledge-mcp truncates text over 80 characters at the last space within the first 80 characters, or at 80 characters without spaces. knowledge-mcp appends `…` after truncation.",
            min_length=1,
        ),
    ]
    under: Annotated[
        str | None,
        Field(
            description="The id of the enclosing heading passage, or null.",
            pattern="^p[1-9][0-9]*$",
        ),
    ]


class ImportAnswer(BaseModel):
    """
    The passages of one source document, with the card questions for every document type that applies.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/import/1"], Field(alias="schema")]
    location: Location
    universe_specs: Annotated[
        list[SpecInScope], Field(description="In kbp_kinds order.", min_length=1)
    ]
    document_types: Annotated[
        list[ImportDocumentType],
        Field(description="Every document type that applies, in kbp_kinds order."),
    ]
    passages: Annotated[
        list[Passage], Field(description="In document order.", min_length=1)
    ]
    received: Received


type KbPrepareImportResult = Annotated[
    ImportAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_prepare_import result, or problem details when isError is true.",
        title="kb_prepare_import result",
    ),
]
