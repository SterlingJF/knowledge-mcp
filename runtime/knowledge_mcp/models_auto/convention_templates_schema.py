# Generated from contracts/extensions/mcp/v1 by just generate_contract_types. Edit the schemas, not this file.

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from ._internal import ConventionContent, ConventionName, Folder, Location
from . import problem_schema


type FolderSource = Annotated[str, Field(min_length=1)]


type NameSource = Annotated[str, Field(min_length=1)]


class ConventionTemplateSource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    title: Annotated[str, Field(min_length=1)]
    url: Annotated[str, Field(pattern="^https://")]


class ConventionTemplateVariant(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Annotated[str, Field(min_length=1)]
    folder_role: Annotated[str, Field(min_length=1)]
    purpose: Annotated[str, Field(min_length=1)]
    folder: Folder | None
    name: ConventionName
    content: ConventionContent | None = None
    folder_sources: list[FolderSource]
    name_sources: list[NameSource]
    adaptation: Annotated[str, Field(min_length=1)]


class ConventionTemplate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: Literal["ace", "para", "johnny-decimal"]
    title: Annotated[str, Field(min_length=1)]
    sources: Annotated[list[ConventionTemplateSource], Field(min_length=1)]
    variants: Annotated[list[ConventionTemplateVariant], Field(min_length=1)]


class ConventionTemplatesAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    schema_: Annotated[
        Literal["knowledge-mcp/convention-templates/1"], Field(alias="schema")
    ]
    location: Location
    templates: Annotated[list[ConventionTemplate], Field(max_length=3, min_length=3)]


type KbListConventionTemplatesResult = Annotated[
    ConventionTemplatesAnswer | problem_schema.ProblemDetails,
    Field(
        description="The naming and filing templates knowledge-mcp ships, with the published source for each choice.",
        title="kb_list_convention_templates result",
    ),
]
