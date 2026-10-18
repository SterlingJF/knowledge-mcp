# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import common_schema, document_types_schema, problem_schema


class Recorded(BaseModel):
    """
    Present when a saved entry sets `no_document_type` or names an applicable universe spec. Send the document-types text as `record` or recall the text through `record_digest`. When `recorded` is present, `candidates` is empty.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    path: common_schema.Path
    label: Literal["from the document-types file"]
    entry: document_types_schema.Entry


class DocumentTypeAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/document-type/1"], Field(alias="schema")]
    location: common_schema.Location
    universe_specs: list[common_schema.SpecInScope]
    candidates: Annotated[
        list[common_schema.Candidate],
        Field(
            description="Candidates with `role_matches` true come first. knowledge-mcp then ranks more file-name matches first, followed by more words in `matched`. Ties keep kbp order."
        ),
    ]
    every_document_type: Annotated[
        list[common_schema.TypeGroup] | None,
        Field(
            description="Null when `recorded` is present or a candidate matched on the file name. Groups with a non-empty `covers_matched` come first."
        ),
    ]
    recorded: Annotated[
        Recorded | None,
        Field(
            description="Present when a saved entry sets `no_document_type` or names an applicable universe spec. Send the document-types text as `record` or recall the text through `record_digest`. When `recorded` is present, `candidates` is empty.",
            title="Recorded",
        ),
    ] = None
    received: common_schema.Received
    filing: list[common_schema.FilingAssessment]


type KbGetDocumentTypeResult = Annotated[
    DocumentTypeAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_get_document_type result, or problem details when isError is true.",
        title="kb_get_document_type result",
    ),
]
