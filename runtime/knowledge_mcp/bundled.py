"""The universe specs and skills copied from knowledge-bus at the pinned ref.

In the plugin folder they sit beside the package; an installed package carries them inside
itself. `KNOWLEDGE_MCP_DATA` names their folder instead: the Homebrew formula sets it to a path
that `brew upgrade` moves to the new version, so skill links keep working.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
PLUGIN = PACKAGE.parent


def _data() -> Path:
    named = os.environ.get("KNOWLEDGE_MCP_DATA", "")
    if os.path.isabs(named):
        return Path(named)
    return PACKAGE if (PACKAGE / "skills").is_dir() else PLUGIN


DATA = _data()
UNIVERSES = DATA / "knowledge-bus" / "universes"
UPSTREAM = DATA / "knowledge-bus" / "UPSTREAM.md"
SKILLS = DATA / "skills"
EXPLORER = SKILLS / "kb-explore" / "runtime"

_REF = re.compile(r"^- Ref: `([^`]+)`$", re.MULTILINE)
_HEADER = re.compile(r"^(universe|guidance):\s*(?:#.*)?$")
_FIELD = re.compile(r"^\s+(id|version):\s*([^#]+?)\s*(?:#.*)?$")


@dataclass(frozen=True)
class Copy:
    """One bundled `*.kbp.yaml` file."""

    name: str
    id: str
    version: str
    path: Path


@cache
def ref() -> str:
    """The knowledge-bus ref of the copies, as recorded in UPSTREAM.md."""
    match = _REF.search(UPSTREAM.read_text(encoding="utf-8"))
    if match is None:
        msg = f"{UPSTREAM} has no pinned ref. Run `just refresh_knowledge_model <ref>`."
        raise RuntimeError(msg)
    return match.group(1)


def label() -> str:
    return f"bundled copy at {ref()}"


def header(text: str) -> tuple[str, str] | None:
    """The id and version in a definition file's header, as written."""
    found: dict[str, str] = {}
    inside = False
    for line in text.splitlines():
        if _HEADER.match(line):
            inside = True
            continue
        if inside and line and not line[0].isspace() and not line.startswith("#"):
            break
        match = _FIELD.match(line) if inside else None
        if match:
            found[match.group(1)] = match.group(2).strip("'\"")
    if "id" in found and "version" in found:
        return found["id"], found["version"]
    return None


@cache
def copies() -> tuple[Copy, ...]:
    """Every bundled `*.kbp.yaml` file, named `<folder>.<file>` so the names stay apart."""
    found = []
    for path in sorted(UNIVERSES.glob("*/*.kbp.yaml")):
        identity = header(path.read_text(encoding="utf-8"))
        if identity is not None:
            found.append(Copy(f"{path.parent.name}.{path.name}", *identity, path))
    return tuple(found)


def skills() -> list[Path]:
    """Every bundled skill folder: knowledge-bus's kb-* and knowledge-mcp's own km-*."""
    return sorted(
        path
        for path in SKILLS.iterdir()
        if path.is_dir()
        and path.name.startswith(("kb-", "km-"))
        and (path / "SKILL.md").is_file()
    )


def index() -> dict[tuple[str, str], Copy]:
    """Bundled files by the id and version in their headers."""
    return {(copy.id, copy.version): copy for copy in copies()}
