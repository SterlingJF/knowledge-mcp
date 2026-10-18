# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import (
    ConventionsFolder,
    FolderConvention,
    InactiveConvention,
    Location,
    Received,
)
from . import problem_schema


class FolderConventionsAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[
        Literal["knowledge-mcp/folder-conventions/1"], Field(alias="schema")
    ]
    location: Location
    folder: ConventionsFolder
    conventions: list[FolderConvention]
    inactive: list[InactiveConvention]
    received: Received


type KbListConventionsResult = Annotated[
    FolderConventionsAnswer | problem_schema.ProblemDetails,
    Field(
        description="The conventions in effect for a folder, each with the folder that declares it and a mark on conventions taken from a parent folder.",
        title="kb_list_conventions result",
    ),
]
