# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import (
    Candidate,
    Digest,
    Entry,
    FileChange,
    FilingAssessment,
    Location,
    Path,
    Received,
    SpecInScope,
    TypeGroup,
)
from . import problem_schema


class Scope(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_specs: list[SpecInScope]
    every_document_type: Annotated[
        list[TypeGroup] | None,
        Field(
            description="Null unless a `to_settle` file references this group through `scope` and has no candidate matching its file name."
        ),
    ]


class UnresolvedFiling(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    question: str


class ChangedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    change: Annotated[
        Literal["settled", "corrected", "moved", "deleted", "kept", "fingerprint"],
        Field(
            description="knowledge-mcp retains every classification field when the universe spec and document type apply at the destination. After a conflicting move, knowledge-mcp retains the original entry and lists the destination in to_settle. Other values name classification, deletion or fingerprint updates."
        ),
    ]
    old_path: Path | None = None
    entry: Entry | None = None
    was: Entry | None = None
    note: str | None = None


class FileToSettle(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    scope: Annotated[int, Field(description="The index into `scopes`.", ge=0)]
    candidates: list[Candidate]
    old_path: Path | None = None
    was: Entry | None = None


class FolderFilingReview(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: str
    recursive: bool
    assessments: list[FilingAssessment]
    unresolved: list[UnresolvedFiling]


class DocumentTypesUpdateAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[
        Literal["knowledge-mcp/document-types-update/1"], Field(alias="schema")
    ]
    location: Location
    based_on: Annotated[
        Digest,
        Field(
            description="Digest of the document-types text sent as `record`, or named by `record_digest`."
        ),
    ]
    record: Annotated[
        str | None,
        Field(
            description="The merged text for the harness to save as `document-types.yaml`. Null when the call sent no `allowed_by`, or when no entry changed and the text sent was not an old `record.yaml`."
        ),
    ]
    digest: Annotated[
        str | None,
        Field(
            description="Digest of `record`, or null when `record` is null. Send a non-null digest as `record_digest` after saving `record`.",
            pattern="^sha256:[0-9a-f]{64}$",
        ),
    ]
    note: Annotated[
        str | None,
        Field(
            description="Present when changes or migration lack `allowed_by`, or when `record` replaces an old `record.yaml`."
        ),
    ] = None
    listing_changes: Annotated[
        list[FileChange] | None,
        Field(
            description="Observed events from comparing the complete listing with saved entries. Present when the call sent `listing`. Retain these events through follow-up classification and naming-value calls. Edited events include first-fingerprint baseline updates."
        ),
    ] = None
    changed: Annotated[
        list[ChangedEntry],
        Field(
            description="Prepared entry changes, including classifications, moves, deletions and fingerprint updates. Use listing_changes to count observed arrivals."
        ),
    ]
    to_settle: Annotated[
        list[FileToSettle],
        Field(
            description="Files that need a document type from the agent, with candidates in kb_get_document_type order."
        ),
    ]
    scopes: Annotated[
        list[Scope],
        Field(
            description="Groups of universe specs that apply, one group for each set of sent `.knowledge-bus/` folders above a file."
        ),
    ]
    received: Received
    filing: Annotated[
        list[FilingAssessment],
        Field(
            description="Assessments for saved entries and candidate types. Join by current path, universe spec and chosen document type. Candidate assessments remain conditional until the document type is chosen. Keep the complete array when capping a conversational preview."
        ),
    ]
    filing_review: Annotated[
        FolderFilingReview | None, Field(title="Folder filing review")
    ] = None


type KbPrepareDocumentTypesResult = Annotated[
    DocumentTypesUpdateAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_prepare_document_types result, or problem details when isError is true.",
        title="kb_prepare_document_types result",
    ),
]
