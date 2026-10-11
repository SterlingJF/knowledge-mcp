"""What a host sends: a document's folders, the universe specs in scope, and file changes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from knowledge_mcp.record import Audience, Event, normal_path


class SpecFile(BaseModel):
    """One `*.kbp.yaml` file in a `.knowledge-bus/` folder."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        description="The file name in `.knowledge-bus/`, ending in `.kbp.yaml`."
    )
    id: str = Field(description="The `id` in the file's header.")
    version: str = Field(description="The `version` in the file's header, as written.")
    text: str | None = Field(
        default=None,
        description=(
            "The full text. Leave it out for a header matching a bundled universe spec. "
            "Send any other file's text once per session, then its digest."
        ),
    )
    digest: str | None = Field(
        default=None,
        description="The digest an earlier answer in this session returned for this text.",
    )

    @field_validator("version", mode="before")
    @classmethod
    def _as_written(cls, value: Any) -> Any:
        if isinstance(value, int | float) and not isinstance(value, bool):
            return str(value)
        return value


class ScopeFolder(BaseModel):
    """One folder on the document's chain that holds a `.knowledge-bus/`."""

    model_config = ConfigDict(extra="forbid")

    depth: int = Field(
        ge=0,
        description=(
            "The number of `folders` entries that lead to this folder: 0 for the knowledge base's "
            "top folder, 1 for the first folder below the top folder."
        ),
    )
    files: list[SpecFile] = Field(
        default_factory=list,
        description=(
            "Every `*.kbp.yaml` file directly inside its `.knowledge-bus/`; empty when the folder "
            "holds none. Leave out `plugins/`, where plugins such as knowledge-mcp keep their files."
        ),
    )
    workspace_yaml: str | None = Field(
        default=None,
        description="The text of `.knowledge-bus/workspace.yaml`, when the folder has one.",
    )


class ScopeRequest(BaseModel):
    """The document's folders and the universe specs on its chain."""

    model_config = ConfigDict(extra="forbid")

    folders: list[str] = Field(default_factory=list)
    universe_specs: list[ScopeFolder] = Field(default_factory=list)


FOLDERS = (
    "Folder names from the knowledge base's top folder down to the folder holding the "
    "document; empty when the document sits in the top folder."
)
UNIVERSE_SPECS = (
    "One entry per folder on that chain holding a `.knowledge-bus/`, empty ones included. "
    "Send none when the chain has no `.knowledge-bus/`. When no folder on the chain holds a "
    "`*.kbp.yaml` file or `workspace.yaml`, the bundled universe specs apply."
)
LOCATION = (
    "The document's location as plain text: a local path, a Drive link or a Notion page. "
    "knowledge-mcp records the text and opens nothing at that location."
)


# --- The fit record ----------------------------------------------------------


class KnowledgeBusFolder(BaseModel):
    """One folder of the knowledge base that holds a `.knowledge-bus/`."""

    model_config = ConfigDict(extra="forbid")

    folder: str = Field(
        description=(
            "The folder's path from the knowledge base's top folder, such as `team/notes`; "
            "empty for the top folder."
        )
    )
    files: list[SpecFile] = Field(
        default_factory=list,
        description=(
            "Every `*.kbp.yaml` file directly inside its `.knowledge-bus/`; empty when the folder "
            "holds none. Leave out `plugins/`, where plugins such as knowledge-mcp keep their files."
        ),
    )
    workspace_yaml: str | None = Field(
        default=None,
        description="The text of `.knowledge-bus/workspace.yaml`, when the folder has one.",
    )


FINGERPRINT = (
    "Text that stays the same while the file's content does, such as `sha256:` and the hex "
    "SHA-256 of the content, or Drive's `md5Checksum`. With fingerprints, a file renamed outside "
    "the agent keeps its entry."
)
RECORD_PATH = (
    "The file's path from the knowledge base's top folder, folders joined by `/`, such as "
    "`docs/rfcs/0042-cache.md`."
)


class ListedFile(BaseModel):
    """One file of the knowledge base, as the host lists the files."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description=RECORD_PATH)
    fingerprint: str | None = Field(default=None, description=FINGERPRINT)


class FileChange(BaseModel):
    """One file created, deleted, moved or edited, as the host reports the change."""

    model_config = ConfigDict(extra="forbid")

    change: Literal["created", "deleted", "moved", "edited"] = Field(
        description="`created`, `deleted`, `moved`, or `edited` with the new fingerprint."
    )
    path: str = Field(description=RECORD_PATH + " For a move, the path after the move.")
    old_path: str | None = Field(
        default=None, description="For a move, the path before the move."
    )
    fingerprint: str | None = Field(default=None, description=FINGERPRINT)

    @model_validator(mode="after")
    def _move_names_both_paths(self) -> FileChange:
        if (self.change == "moved") != (self.old_path is not None):
            msg = "send `old_path` with a move, and only with a move"
            raise ValueError(msg)
        if self.change == "edited" and self.fingerprint is None:
            msg = "send the new `fingerprint` with an edit"
            raise ValueError(msg)
        return self

    def event(self) -> Event:
        """The change as the record merge applies it."""
        old = normal_path(self.old_path) if self.old_path else None
        kind = "fingerprint" if self.change == "edited" else self.change
        return (kind, normal_path(self.path), old, self.fingerprint)


class FitItem(BaseModel):
    """One file's fit, settled by the agent or stated by the person."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description=RECORD_PATH)
    made: Literal["fit", "correction"] = Field(
        description=(
            "`fit` for a fit you settled; `correction` for a fit or reader the person stated."
        )
    )
    universe_spec: str | None = Field(
        default=None, description="The universe spec id of the document type."
    )
    kind: str | None = Field(default=None, description="The document type id.")
    no_fit: bool = Field(
        default=False, description="True when no document type in scope fits the file."
    )
    audience: Audience | None = Field(
        default=None,
        description=(
            "The document's reader: `value` from `kb_audience`'s choices, or the actor; "
            "`status` `confirmed` once the person confirmed the value, else `guessed`."
        ),
    )
