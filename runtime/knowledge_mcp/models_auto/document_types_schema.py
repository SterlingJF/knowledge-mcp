# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from . import common_schema


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
    fingerprint: common_schema.Fingerprint | None = None
    time: common_schema.Time


class UntypedEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    no_document_type: Literal[True]
    audience: Audience | None = None
    set_by: SetBy
    allowed_by: AllowedBy | None = None
    fingerprint: common_schema.Fingerprint | None = None
    time: common_schema.Time


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
