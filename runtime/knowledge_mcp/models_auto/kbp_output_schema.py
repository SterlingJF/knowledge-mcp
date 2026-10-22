# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import Received
from . import problem_schema


class KbpOutputNote(BaseModel):
    """
    The existing knowledge-mcp receipt, when present.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: Annotated[str | None, Field(description="The bundled source label.")] = None
    bundled: Annotated[
        list[str] | None, Field(description="Bundled universe spec identifiers.")
    ] = None
    received: Received | None = None
    explorer: Annotated[
        str | None,
        Field(description="The existing viewer folder path, on successful explore."),
    ] = None


class KbpOutputAnswer(BaseModel):
    """
    A receipt for a successful upstream call, without parsing or rewriting its text. This contract describes the wrapper, not upstream formats.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[Literal["knowledge-mcp/kbp-output/1"], Field(alias="schema")]
    stdout: Annotated[
        str, Field(description="The exact captured stdout, including whitespace.")
    ]
    stderr: Annotated[
        str, Field(description="The exact captured stderr, including whitespace.")
    ]
    exit_code: Annotated[
        Literal[0],
        Field(description="Zero on success; nonzero exits return problem details."),
    ]
    note: Annotated[
        KbpOutputNote | None,
        Field(
            description="The existing knowledge-mcp receipt, when present.",
            title="Kbp output note",
        ),
    ] = None


type KbpToolResult = Annotated[
    KbpOutputAnswer | problem_schema.ProblemDetails,
    Field(
        description="The structuredContent of every kbp tool. Raw upstream text remains in the original content blocks. Failures use the existing problem details shape.",
        title="kbp tool result",
    ),
]
