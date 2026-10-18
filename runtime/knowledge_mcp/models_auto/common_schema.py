# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


type SharedShapes = Annotated[
    Any,
    Field(
        description="Definitions shared by the tool results and the document-types file.",
        title="Shared shapes",
    ),
]


type Location = Annotated[str, Field(title="Location")]


type Path = Annotated[
    str,
    Field(
        description="Path from the knowledge base's root folder, with `/` between folders, such as `docs/rfcs/0042-cache.md`.",
        min_length=1,
        title="Path",
    ),
]


type Fingerprint = Annotated[
    str,
    Field(
        description="A value that changes only when the file content changes, such as SHA-256 or Drive's `md5Checksum`. kb_prepare_document_types uses fingerprints to find files in `listing` that moved.",
        title="Fingerprint",
    ),
]


type Digest = Annotated[
    str,
    Field(
        description="The SHA-256 of the text's UTF-8 bytes.",
        pattern="^sha256:[0-9a-f]{64}$",
        title="Digest",
    ),
]


type Time = Annotated[
    str,
    Field(
        description="ISO 8601 date and time in UTC.",
        pattern="^\\d{4}-\\d{2}-\\d{2}T.*Z$",
        title="Time",
    ),
]


type EditId = Annotated[str, Field(pattern="^[0-9a-f]{32}$", title="Edit id")]


class ReceivedText(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    digest: Digest


type Received = Annotated[
    list[ReceivedText],
    Field(
        description="Digests of the texts sent in this call. Later in the session, send a digest in place of its text.",
        title="Received",
    ),
]
"""
Digests of the texts sent in this call. Later in the session, send a digest in place of its text.
"""


class SpecInScope(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[str, Field(min_length=1)]
    version: str
    source: Annotated[
        str,
        Field(
            description="`bundled copy at <ref>` means knowledge-mcp used its own copy of the universe spec, taken from git ref `<ref>` of the knowledge-bus repository.",
            pattern="^(sent by the harness|bundled copy at \\S+)$",
        ),
    ]
    from_parent: Annotated[
        bool,
        Field(
            description="True when the universe spec comes from a `.knowledge-bus/` folder above the deepest `.knowledge-bus/` folder the harness sent."
        ),
    ]


class Alias(BaseModel):
    """
    From kbp_kinds.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    kind: Literal["descriptive", "normative"] | None = None
    form: str | None = None


class Candidate(BaseModel):
    """
    A document type whose alias shares a word with the file name or its nearest folder.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    name: str
    alias: Annotated[Alias | None, Field(description="From kbp_kinds.", title="Alias")]
    action: str | None
    actor: str | None
    timing: str | None
    matched: Annotated[
        list[str],
        Field(
            description="Words shared by the alias and the file name or nearest folder, lowercased with common plural suffixes removed.",
            min_length=1,
        ),
    ]
    matched_on: Annotated[
        Literal["name", "folder"],
        Field(description="`folder` means only the nearest folder name matched."),
    ]
    role_matches: Annotated[
        bool | None,
        Field(
            description="True when `actor` and the role share a normalized word after knowledge-mcp removes stopwords. Present only when the harness sent a role."
        ),
    ] = None


class ListedDocumentType(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    document_type: Annotated[str, Field(min_length=1)]
    action: str | None
    actor: str | None


class TypeGroup(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    covers: str | None
    covers_matched: Annotated[
        list[str],
        Field(
            description="Words in the path that also appear in the universe spec label or `covers`."
        ),
    ]
    kinds: list[ListedDocumentType]


class FileCreated(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["created"]
    path: Path
    fingerprint: Fingerprint | None = None


class FileDeleted(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["deleted"]
    path: Path


class FileMoved(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["moved"]
    path: Annotated[Path, Field(description="The path after the move.")]
    old_path: Path
    fingerprint: Fingerprint | None = None


class FileEdited(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    change: Literal["edited"]
    path: Path
    fingerprint: Fingerprint


class ListedFile(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    fingerprint: Fingerprint | None = None


class FolderCount(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: str
    count: Annotated[int, Field(ge=1)]


class FilingProposal(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: str
    name: str
    path: Path
    folder_new: Literal[False]
    name_style: Literal["lower-kebab", "lower-snake", "unchanged"]
    evidence: list[Path]
    folder_counts: list[FolderCount]


class FilingProposal3(FilingProposal):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: str
    name: str
    path: Path
    folder_new: Literal[False]
    name_style: Literal["lower-kebab", "lower-snake", "unchanged"]
    evidence: list[Path]
    folder_counts: list[FolderCount]


type FilingProposal1 = Annotated[
    FilingProposal3 | FilingProposal, Field(title="Filing proposal")
]


class FilingAssessment1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    status: Literal["proposed"]
    proposal: Annotated[FilingProposal1 | None, Field(title="Filing proposal")]


class FilingAssessment2(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    status: Literal[
        "proposed",
        "already_matches",
        "no_peers",
        "no_document_type",
        "document_type_needed",
        "listing_needed",
        "evidence_incomplete",
        "destination_occupied",
        "already_matches",
        "no_peers",
        "listing_needed",
        "evidence_incomplete",
        "destination_occupied",
    ]
    proposal: FilingProposal | None


class FilingAssessment3(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: None
    document_type: None
    status: Literal[
        "proposed",
        "already_matches",
        "no_peers",
        "no_document_type",
        "document_type_needed",
        "listing_needed",
        "evidence_incomplete",
        "destination_occupied",
        "no_document_type",
        "document_type_needed",
    ]
    proposal: FilingProposal | None


type FilingAssessment = Annotated[
    FilingAssessment1 | FilingAssessment2 | FilingAssessment3,
    Field(title="Filing assessment"),
]


type MovePath = Annotated[
    str,
    Field(
        description="Path relative to the knowledge-base root, with forward slashes between folders.",
        min_length=1,
        pattern="^[^/\\\\\\u0000]+(?:/[^/\\\\\\u0000]+)*$",
        title="Move path",
    ),
]


class MoveDocument(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: MovePath
    text: str


class LinkBinding(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    source_path: MovePath
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]
    target_path: MovePath


type FileChange = Annotated[
    FileCreated | FileDeleted | FileMoved | FileEdited, Field(title="File change")
]
