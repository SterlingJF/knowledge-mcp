# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import common_schema, document_types_schema, problem_schema


class Scope(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_specs: list[common_schema.SpecInScope]
    every_document_type: Annotated[
        list[common_schema.TypeGroup] | None,
        Field(
            description="Null unless a `to_settle` file references this group through `scope` and has no candidate matching its file name."
        ),
    ]


class ChangedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: common_schema.Path
    change: Annotated[
        Literal["settled", "corrected", "moved", "deleted", "kept", "fingerprint"],
        Field(
            description="`settled` means the agent set the entry. `corrected` means the person set the entry. A `moved` item has `entry` when the person set the entry or confirmed the reader. A typed entry also needs its universe spec to apply at the new path. Other `moved` items have `was`, and `to_settle` lists the file. `deleted` items have `was`. `fingerprint` means knowledge-mcp updated the stored fingerprint. `kept` means an entry with `set_by: person` overrode an agent entry from `entries`."
        ),
    ]
    old_path: common_schema.Path | None = None
    entry: document_types_schema.Entry | None = None
    was: document_types_schema.Entry | None = None
    note: str | None = None


class FileToSettle(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: common_schema.Path
    scope: Annotated[int, Field(description="The index into `scopes`.", ge=0)]
    candidates: list[common_schema.Candidate]
    old_path: common_schema.Path | None = None
    was: document_types_schema.Entry | None = None


class DocumentTypesUpdateAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[
        Literal["knowledge-mcp/document-types-update/1"], Field(alias="schema")
    ]
    location: common_schema.Location
    based_on: Annotated[
        common_schema.Digest,
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
            description="Digest of `record`, or null when `record` is null. Send a non-null digest as `record_digest` in the next call.",
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
        list[common_schema.FileChange] | None,
        Field(
            description="File changes that knowledge-mcp found by comparing `listing` with the entries. Present only when the call sent `listing`."
        ),
    ] = None
    changed: list[ChangedEntry]
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
    received: common_schema.Received


type KbPrepareDocumentTypesResult = Annotated[
    DocumentTypesUpdateAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_prepare_document_types result, or problem details when isError is true.",
        title="kb_prepare_document_types result",
    ),
]
