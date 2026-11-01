# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from pydantic import BaseModel, ConfigDict, Field
from ._internal import Digest, Path, Time
from typing import Annotated, Literal
from . import problem_schema


class ProposalInputs(BaseModel):
    """
    The input digest to recheck before saving. Present when `document_digest` was sent.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    document_digest: Digest


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
    file: Annotated[
        str,
        Field(
            description="The file's path as you read it, such as `meeting-notes.md`.",
            min_length=1,
        ),
    ]
    line_number: Annotated[
        int, Field(description="The 1-based line number in that file.", ge=1)
    ]


class PlaceSource(BaseModel):
    """
    A place in a sheet or deck.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[
        str,
        Field(
            description="The sheet or deck's path as you read it, such as `build-timings.xlsx`.",
            min_length=1,
        ),
    ]
    place: Annotated[
        str, Field(description="Such as `Evening!A2:D10` or `slide 7`.", min_length=1)
    ]


class FileSource(BaseModel):
    """
    A whole file, with no line or place, such as a sheet you read in full.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[
        str,
        Field(
            description="The file's path as you read it, such as `build-timings.xlsx`.",
            min_length=1,
        ),
    ]


class PersonSource(BaseModel):
    """
    The person's words in this conversation.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    said: Annotated[
        str,
        Field(
            description="What the person said, quoted or closely paraphrased.",
            min_length=1,
        ),
    ]


class ProposalDocumentType(BaseModel):
    """
    The document's type, from kb_get_document_type. Send it whenever you know it.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[str, Field(description="Such as `design-proposal`.", min_length=1)]
    label: Annotated[str, Field(description="Such as `Design proposal`.", min_length=1)]


class ProposalReader(BaseModel):
    """
    The audience choice the document is for, from kb_list_audiences. Set `confirmed` false when you guessed it.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[
        str,
        Field(
            description="The audience's id, as kb_list_audiences returned it.",
            min_length=1,
        ),
    ]
    label: Annotated[
        str,
        Field(
            description="Such as `maintainers deciding whether to accept it`.",
            min_length=1,
        ),
    ]
    confirmed: Annotated[
        bool,
        Field(
            description="True when the person confirmed the reader, false when it's your guess."
        ),
    ]


class FilingNote(BaseModel):
    """
    Where a new document will be saved and why. Omit it for an existing document.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    path: Path
    naming_rule: Annotated[
        str | None,
        Field(
            description="The naming rule that named the file, or null when none applied.",
            min_length=1,
        ),
    ]
    reason: Annotated[
        str | None,
        Field(
            description="Why you chose the path. Required when `naming_rule` is null.",
            min_length=1,
        ),
    ] = None


class LeftOutFile(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    file: Annotated[
        str,
        Field(description="The path of a file you read but didn't cite.", min_length=1),
    ]
    reason: Annotated[
        str, Field(description="Why you left the file out, in one line.", min_length=1)
    ]


class ProposalInstance(BaseModel):
    """
    Identifies this card among earlier cards for the same document. A card with a later `created_at`, then a higher `seq`, supersedes it. Ordering uses server wall-clock time, then `seq`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    subject: Annotated[
        str,
        Field(
            description="The document the proposal is about, as sent in `location`.",
            min_length=1,
        ),
    ]
    created_at: Time
    seq: Annotated[
        int,
        Field(
            description="Counts up with each proposal this server process prepares.",
            ge=1,
        ),
    ]


class ProposalRow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    current: Annotated[
        ProposalCell | None,
        Field(description="The document's text now. Omit it for an addition."),
    ] = None
    proposed: Annotated[
        ProposalCell, Field(description="The text you propose, in place of `current`.")
    ]
    mark: EvidenceMark | None = None
    sources: Annotated[
        list[LineSource | PlaceSource | PersonSource | FileSource],
        Field(
            description="Where the proposed text comes from. Cite at least one source per row.",
            min_length=1,
        ),
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
    document_type: Annotated[
        ProposalDocumentType | None,
        Field(description="The document's type, from kb_get_document_type."),
    ] = None
    reader: Annotated[
        ProposalReader | None,
        Field(
            description="Who the document is for, from kb_list_audiences, and whether the person confirmed it."
        ),
    ] = None
    filing: Annotated[
        FilingNote | None,
        Field(
            description="For a new document, where it will be saved and whether a naming rule applied. Omit it for an existing document."
        ),
    ] = None
    open_questions: Annotated[
        list[ProposalCell] | None,
        Field(description="Questions no source answers, apart from conflicting rows."),
    ] = None
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
    based_on: Annotated[
        ProposalInputs | None,
        Field(
            description="The input digest to recheck before saving. Present when `document_digest` was sent.",
            title="Proposal inputs",
        ),
    ] = None
    instance: ProposalInstance | None = None


type KbPrepareProposalResult = Annotated[
    Proposal | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of a kb_prepare_proposal result, or problem details when isError is true.",
        title="kb_prepare_proposal result",
    ),
]
