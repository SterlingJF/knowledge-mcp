from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from knowledge_mcp import bundled, kbp, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.models import KnowledgeBusFolder, ScopeRequest
from knowledge_mcp.scope import SENT, Rebuilt, ScopeError, Workspace

if TYPE_CHECKING:
    from knowledge_mcp.conventions import Filing


def kinds_of(listing: dict[str, Any]) -> records.Kinds:
    return {
        group["universe_spec"]["id"]: (
            str(group["universe_spec"]["version"]),
            frozenset(kind["kind"] for kind in group["kinds"]),
        )
        for group in listing.get("universe_specs", [listing])
    }


def scope_specs(listing: dict[str, Any], rebuilt: Rebuilt) -> list[dict[str, Any]]:
    groups = listing.get("universe_specs", [listing])
    parents = set(listing.get("from_parent", []))
    return [
        {
            "id": spec["id"],
            "version": spec["version"],
            "source": rebuilt.sources.get(spec["id"], SENT),
            "from_parent": spec["id"] in parents
            or (rebuilt.nearest is not None and spec["id"] not in rebuilt.nearest),
        }
        for spec in (group["universe_spec"] for group in groups)
    ]


def listed_kinds(
    workspace: Workspace, request: ScopeRequest
) -> tuple[dict[str, Any], Rebuilt]:
    """Raise KbpFailed when kbp exits nonzero."""
    with workspace.rebuilt(request) as rebuilt:
        output = kbp.run(["--kinds"], rebuilt.cwd)
    if output.code != 0:
        raise problems.KbpFailed(output, "kinds")
    return kbp.parsed(output, "kinds", kbp.KINDS), rebuilt


@dataclass
class Scope:
    index: int
    listing: dict[str, Any]
    specs: list[dict[str, Any]]
    kinds: records.Kinds
    wants_every: bool = False


@dataclass
class Scopes:
    """Run `kbp --kinds` once for each set of `.knowledge-bus/` folders that apply to a file,
    and cache each result.

    Raise ScopeError when `knowledge_bus_folders` names a folder more than once.
    """

    workspace: Workspace
    folders: list[KnowledgeBusFolder]
    found: dict[tuple[tuple[str, ...], ...], Scope] = field(default_factory=dict)
    received: dict[str, dict[str, Any]] = field(default_factory=dict)
    conventions: Filing | None = None

    def __post_init__(self) -> None:
        seen = set()
        for index, item in enumerate(self.folders):
            parts = _parts(item.folder, index)
            if parts in seen:
                msg = (
                    f"Send each folder once in `knowledge_bus_folders`. {item.folder!r} "
                    "appears more than once."
                )
                raise ScopeError(
                    msg,
                    pointer=problems.pointer("knowledge_bus_folders", index, "folder"),
                )
            seen.add(parts)

    def at(self, path: str) -> Scope:
        chain = path.split("/")[:-1]
        applicable = sorted(
            (
                (_parts(item.folder, index), index, item)
                for index, item in enumerate(self.folders)
                if list(_parts(item.folder, index))
                == chain[: len(_parts(item.folder, index))]
            ),
            key=lambda found: len(found[0]),
        )
        key = tuple(parts for parts, _, _ in applicable)
        if key in self.found:
            return self.found[key]
        request = ScopeRequest(
            folders=list(applicable[-1][0]) if applicable else [],
            knowledge_bus_folders=[item for _, _, item in applicable],
            positions=[index for _, index, _ in applicable],
        )
        listing, rebuilt = listed_kinds(self.workspace, request)
        for item in rebuilt.received:
            self.received[str(item["digest"])] = item
        scope = Scope(
            len(self.found), listing, scope_specs(listing, rebuilt), kinds_of(listing)
        )
        self.found[key] = scope
        return scope

    def definition(self, path: str, identity: str) -> tuple[str, ...]:
        self.at(path)
        chain = sorted(
            (
                f
                for f in self.folders
                if not f.folder or path.startswith(f.folder + "/")
            ),
            key=lambda f: len(f.folder),
        )
        for folder in reversed(chain):
            specs = [s for s in folder.files if s.id == identity]
            if specs:
                texts = []
                for spec in specs:
                    text = (
                        spec.text
                        if spec.text is not None
                        else self.workspace.recall(spec.digest)
                        if spec.digest
                        else None
                    )
                    if text is None:
                        copy = bundled.index().get((spec.id, spec.version))
                        text = copy.path.read_text(encoding="utf-8") if copy else ""
                    texts.append(records.digest(text))
                return tuple(sorted(texts))
        copies = [c for c in bundled.copies() if c.id == identity]
        return tuple(
            sorted(records.digest(c.path.read_text(encoding="utf-8")) for c in copies)
        )

    def same_definition(self, first: str, second: str, identity: str) -> bool:
        return self.definition(first, identity) == self.definition(second, identity)

    def validate_conventions(self, path: str) -> None:
        if self.conventions is not None and self.conventions.context is not None:
            self.conventions.at(path)

    def allows_transfer(self, first: str, second: str, key: tuple[str, str]) -> bool:
        kinds = self.kinds_at(second)
        universe, kind = key
        return (
            universe in kinds
            and kind in kinds[universe][1]
            and self.same_definition(first, second, universe)
        )

    def kinds_at(self, path: str) -> records.Kinds:
        return self.at(path).kinds


def _parts(folder: str, index: int) -> tuple[str, ...]:
    if folder in ("", "."):
        return ()
    pointer = problems.pointer("knowledge_bus_folders", index, "folder")
    return tuple(records.normal_path(folder, pointer=pointer).split("/"))
