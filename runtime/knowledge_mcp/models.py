from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from knowledge_mcp.models_auto.common_schema import FileChange, ListedFile
from knowledge_mcp.models_auto.document_types_schema import AllowedBy, Audience, SetBy

__all__ = [
    "AllowedBy",
    "Audience",
    "EntryItem",
    "FileChange",
    "KnowledgeBusFolder",
    "ListedFile",
    "ScopeRequest",
    "SpecFile",
]


class SpecFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="The file name, such as `universe.kbp.yaml`.")
    id: str = Field(
        description="The `id` value in the file's `universe:` or `guidance:` block."
    )
    version: str = Field(
        description=(
            "The `version` value in the file's `universe:` or `guidance:` block, as written."
        )
    )
    text: str | None = Field(
        default=None,
        description=(
            "The full file text. Send fresh text whenever the file changes. Reuse `digest` while the text stays unchanged. Leave it "
            "out when `id` and `version` match a bundled file, except in kbp_validate."
        ),
    )
    # Leave digests unconstrained so malformed and unknown digests both prompt for file text.
    digest: str | None = Field(
        default=None,
        description=(
            "File SHA-256 (`sha256:…`); send exact text if unknown. kbp_validate requires previously sent text."
        ),
    )

    @field_validator("version", mode="before")
    @classmethod
    def _as_written(cls, value: Any) -> Any:
        if isinstance(value, int | float) and not isinstance(value, bool):
            return str(value)
        return value


class KnowledgeBusFolder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    folder: str = Field(
        description=(
            "Path from the knowledge-base root, such as `team/notes`. Empty for the root folder."
        )
    )
    files: list[SpecFile] = Field(
        default_factory=list,
        description="Every `*.kbp.yaml` file directly inside the `.knowledge-bus/` folder.",
    )
    workspace_yaml: str | None = Field(
        default=None,
        description="The text of `.knowledge-bus/workspace.yaml`.",
    )


class ScopeRequest(BaseModel):
    """`positions[i]` maps `knowledge_bus_folders[i]` to its index in the tool call's `knowledge_bus_folders` argument.

    Set `positions` for a subset of the sent folders so JSON pointers in errors identify the original arguments.
    """

    model_config = ConfigDict(extra="forbid")

    folders: list[str] = Field(default_factory=list)
    knowledge_bus_folders: list[KnowledgeBusFolder] = Field(default_factory=list)
    positions: list[int] | None = None


KNOWLEDGE_BUS_FOLDERS = (
    "One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to "
    "the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no "
    "entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. "
    "kbp_validate returns an error instead."
)
RECORD_PATH = (
    "Path from the knowledge-base root, folders joined by `/`, such as "
    "`docs/rfcs/0042-cache.md`."
)


class EntryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description=RECORD_PATH)
    set_by: SetBy = Field(
        description=(
            "`agent` when you chose the document type or reader. "
            "`person` when the person stated the document type or reader."
        )
    )
    universe_spec: str | None = Field(
        default=None,
        description="Id of the universe spec that declares `document_type`.",
    )
    document_type: str | None = None
    no_document_type: bool = False
    audience: Audience | None = Field(
        default=None,
        description=(
            "The document's reader. `value` is one of the `choices` or the `actor` from "
            "`kb_list_audiences`. Set `status` to `confirmed` only after the person confirms "
            "the value."
        ),
    )
