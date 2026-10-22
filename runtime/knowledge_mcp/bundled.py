"""Bundled universe specs, `type-guidance.kbp.yaml` files and skills."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from knowledge_mcp.errors import InstallFault

PACKAGE = Path(__file__).resolve().parent
PLUGIN = PACKAGE.parent


def _data() -> Path:
    """Return an absolute `KNOWLEDGE_MCP_DATA`, else the package folder in a wheel, else the plugin
    folder.

    Homebrew sets `KNOWLEDGE_MCP_DATA` to the `opt` path, which survives `brew upgrade`, so skill
    links keep working.
    """
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
    name: str
    id: str
    version: str
    path: Path


def _missing() -> InstallFault:
    return InstallFault(f"Bundled files are missing from {DATA}.")


@cache
def ref() -> str:
    """Raise `InstallFault` when UPSTREAM.md is missing or names no ref."""
    try:
        text = UPSTREAM.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise _missing() from None
    match = _REF.search(text)
    if match is None:
        msg = f"{UPSTREAM} names no knowledge-bus ref."
        raise InstallFault(msg)
    return match.group(1)


def fault() -> InstallFault | None:
    """Return an `InstallFault` when the bundled universe specs, skills or ref are missing."""
    if not any(UNIVERSES.glob("*/*.kbp.yaml")) or not skills():
        return _missing()
    try:
        ref()
    except InstallFault as error:
        return error
    return None


def require() -> None:
    found = fault()
    if found is not None:
        raise found


def label() -> str:
    return f"bundled copy at {ref()}"


def header(text: str) -> tuple[str, str] | None:
    """Return `id` and `version` from the `universe:` or `guidance:` block.

    Read the lines directly, so a file with invalid YAML elsewhere still gives its header. Return
    None when either field is missing.
    """
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
    """Use `<folder>.<file>` names because the bundled folders share file names."""
    found = []
    for path in sorted(UNIVERSES.glob("*/*.kbp.yaml")):
        identity = header(path.read_text(encoding="utf-8").removeprefix("\ufeff"))
        if identity is not None:
            found.append(Copy(f"{path.parent.name}.{path.name}", *identity, path))
    return tuple(found)


def skills() -> list[Path]:
    if not SKILLS.is_dir():
        return []
    return sorted(
        path
        for path in SKILLS.iterdir()
        if path.is_dir()
        and path.name.startswith("kb-")
        and (path / "SKILL.md").is_file()
    )


def index() -> dict[tuple[str, str], Copy]:
    return {(copy.id, copy.version): copy for copy in copies()}
