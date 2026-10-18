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
    folder_new: bool
    name_style: Literal["lower-kebab", "lower-snake", "unchanged", "convention"]
    evidence: list[Path]
    folder_counts: list[FolderCount]


class FilingProposal3(FilingProposal):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: str
    name: str
    path: Path
    folder_new: bool
    name_style: Literal["lower-kebab", "lower-snake", "unchanged", "convention"]
    evidence: list[Path]
    folder_counts: list[FolderCount]


type FilingProposal1 = Annotated[
    FilingProposal3 | FilingProposal, Field(title="Filing proposal")
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


class FilingValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    properties: dict[str, str] | None = {}
    content: str | None = None


class NeededValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    source: Literal["property", "content"]
    name: Annotated[str, Field(min_length=1)]


type ConventionsFolder = Annotated[
    str,
    Field(
        pattern="^(?:[^/\\\\\\u0000]+(?:/[^/\\\\\\u0000]+)*)?$",
        title="Conventions folder",
    ),
]


class ConventionFile1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: ConventionsFolder
    text: str
    digest: Digest | None = None


class ConventionFile2(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    folder: ConventionsFolder
    text: str | None = None
    digest: Digest


type ConventionFile = Annotated[
    ConventionFile1 | ConventionFile2, Field(title="Convention file")
]


type FileChange = Annotated[
    FileCreated | FileDeleted | FileMoved | FileEdited, Field(title="File change")
]


class ConventionSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    file: Literal[".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"]
    folder: ConventionsFolder
    from_parent: bool
    digest: Digest
    definition: SavedConvention


class FolderConvention(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: str
    document_type: str
    source: ConventionSource
    base_folder: ConventionsFolder


class InactiveConvention(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: str
    document_type: str
    source: ConventionSource
    reason: Literal["document_type_unavailable", "definition_differs"]


class FilingAssessment1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    status: Literal["proposed"]
    proposal: Annotated[FilingProposal1 | None, Field(title="Filing proposal")]
    convention: ConventionSource | None = None
    needed: Annotated[list[NeededValue] | None, Field(min_length=1)] = None


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
        "destination_type_conflict",
        "destination_occupied",
        "values_needed",
        "already_matches",
        "no_peers",
        "listing_needed",
        "evidence_incomplete",
        "destination_type_conflict",
        "destination_occupied",
    ]
    proposal: FilingProposal | None
    convention: ConventionSource | None = None
    needed: Annotated[list[NeededValue] | None, Field(min_length=1)] = None


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
        "destination_type_conflict",
        "destination_occupied",
        "values_needed",
        "no_document_type",
        "document_type_needed",
    ]
    proposal: FilingProposal | None
    convention: ConventionSource | None = None
    needed: Annotated[list[NeededValue] | None, Field(min_length=1)] = None


class FilingAssessment4(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    status: Literal["values_needed"]
    proposal: FilingProposal | None
    convention: ConventionSource
    needed: Annotated[list[NeededValue], Field(min_length=1)]


type FilingAssessment = Annotated[
    FilingAssessment1 | FilingAssessment2 | FilingAssessment3 | FilingAssessment4,
    Field(title="Filing assessment"),
]


class ConventionDocumentTypePart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    part: Literal["document_type"]


class ConventionDatePart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    part: Literal["date"]
    property: Annotated[str, Field(min_length=1)]
    format: Literal["YYYY-MM-DD", "YYYY-MM", "YYYY"]


class ConventionPropertyPart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    part: Literal["property"]
    property: Annotated[str, Field(min_length=1)]


class ConventionContentPart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    part: Literal["content"]


class ConventionContent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    label: Annotated[str, Field(min_length=1)]
    instruction: Annotated[str, Field(min_length=1)]


class ConventionReference(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]


type ConventionSegment = Annotated[
    str,
    Field(
        min_length=1,
        pattern="^[^#|^:/\\\\\\[\\]\\u0000-\\u001f\\u007f-\\u009f]+$",
        title="Convention segment",
    ),
]


class ConventionLiteralPart(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    part: Literal["literal"]
    value: ConventionSegment


type Part = Annotated[
    ConventionDocumentTypePart
    | ConventionDatePart
    | ConventionPropertyPart
    | ConventionContentPart
    | ConventionLiteralPart,
    Field(title="Convention part"),
]


class ConventionName(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    separator: Literal[" ", "-", "_"]
    case: Literal["as-written", "lower"] | None = "as-written"
    parts: Annotated[list[Part], Field(min_length=1)]


class SavedConvention(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    document_type: Annotated[str, Field(min_length=1)]
    folder: list[ConventionSegment | Part]
    name: ConventionName
    content: ConventionContent | None = None
    set_by: SetBy
    allowed_by: AllowedBy
    time: Time


type Folder = list[ConventionSegment | Part]


class NamingAndFilingConventions(BaseModel):
    """
    Saved conventions for document types in the declaring folder.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/conventions/1"], Field(alias="schema")]
    from_parent: list[ConventionReference]
    conventions: list[SavedConvention]


type FileKey = Annotated[
    str,
    Field(
        description="Path from the root folder with `/` between folders. Empty, `.` and `..` parts and backslashes are invalid.",
        pattern="^(?:[^/\\\\.][^/\\\\]*|\\.[^/\\\\.][^/\\\\]*|\\.\\.[^/\\\\]+)(?:/(?:[^/\\\\.][^/\\\\]*|\\.[^/\\\\.][^/\\\\]*|\\.\\.[^/\\\\]+))*$",
        title="File key",
    ),
]


class Audience(BaseModel):
    """
    The document's reader, and whether the person confirmed the value.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    value: str
    status: Literal["confirmed", "guessed"]


class AllowedBy(BaseModel):
    """
    The person's permission for the save or the edit.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    basis: Annotated[
        Literal["request", "instruction", "accepted_change"],
        Field(
            description="`request` means the person asked in this session. `instruction` means the person wrote an instruction for agents, such as in AGENTS.md. `accepted_change` means the person accepted a proposed change."
        ),
    ]
    text: Annotated[
        str,
        Field(
            description="The request, instruction or accepted change, quoted.",
            min_length=1,
        ),
    ]
    location: Annotated[
        str | None,
        Field(description="The file holding the instruction or the accepted change."),
    ] = None


type SetBy = Annotated[
    Literal["agent", "person"],
    Field(
        description="`person` when the person stated the document type or reader. An entry the person set wins over any later entry by the agent.",
        title="Set by",
    ),
]


class TypedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    universe_spec: Annotated[str, Field(min_length=1)]
    version: str
    document_type: Annotated[str, Field(min_length=1)]
    audience: Audience | None = None
    set_by: SetBy
    allowed_by: AllowedBy | None = None
    fingerprint: Fingerprint | None = None
    time: Time


class UntypedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    no_document_type: Literal[True]
    audience: Audience | None = None
    set_by: SetBy
    allowed_by: AllowedBy | None = None
    fingerprint: Fingerprint | None = None
    time: Time


class SavedEntry1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    allowed_by: AllowedBy


class SavedEntry2(TypedEntry, SavedEntry1):
    model_config = ConfigDict(
        extra="forbid",
    )


class SavedEntry3(UntypedEntry, SavedEntry1):
    model_config = ConfigDict(
        extra="forbid",
    )


type SavedEntry = Annotated[SavedEntry2 | SavedEntry3, Field(title="Saved entry")]


class DocumentTypes(BaseModel):
    """
    The document-types file, `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` at the knowledge base's root folder. Each entry maps a file's path to a universe spec and document type, or to `no_document_type`, plus an optional reader. The harness reads and writes the file and creates missing folders.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/document-types/1"], Field(alias="schema")]
    files: dict[FileKey, SavedEntry]


type Entry = Annotated[TypedEntry | UntypedEntry, Field(title="Entry")]
