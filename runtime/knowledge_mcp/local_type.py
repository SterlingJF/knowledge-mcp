"""Run kb_get_document_type in process for `kb type <path>`."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

import anyio
import yaml

from knowledge_mcp import bundled, conventions, problems
from knowledge_mcp import document_types as records
from knowledge_mcp.errors import ToolFault, UsageFault
from knowledge_mcp.main import build_server
from knowledge_mcp.models import KnowledgeBusFolder, ScopeRequest
from knowledge_mcp.scope import Workspace
from knowledge_mcp.type_scope import listed_kinds

KNOWLEDGE_BUS = ".knowledge-bus"


def _from_parent(knowledge_bus: Path) -> bool:
    """Return False when `workspace.yaml` is missing, unreadable or not valid YAML."""
    workspace = knowledge_bus / "workspace.yaml"
    if not workspace.is_file():
        return False
    try:
        data = yaml.safe_load(workspace.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, yaml.YAMLError:
        return False
    return isinstance(data, dict) and bool(data.get("from_parent"))


def root_folder(folder: Path) -> Path:
    """Walk upward through folders containing `.knowledge-bus/`.

    Return the first folder where `workspace.yaml` omits or disables `from_parent`.
    Use the topmost folder containing `.knowledge-bus/` even when `from_parent` is enabled.
    With no `.knowledge-bus/`, use the nearest folder holding `.git`.
    With neither marker, use the parent of `folder` so kb can match the folder name against document types.
    """
    chain = (folder, *folder.parents)
    found = [candidate for candidate in chain if (candidate / KNOWLEDGE_BUS).is_dir()]
    for index, candidate in enumerate(found):
        if index + 1 == len(found) or not _from_parent(candidate / KNOWLEDGE_BUS):
            return candidate
    for candidate in chain:
        if (candidate / ".git").exists():
            return candidate
    return folder.parent


def _spec_files(
    knowledge_bus: Path, index: dict[tuple[str, str], bundled.Copy]
) -> list[dict[str, Any]]:
    files = []
    for path in sorted(knowledge_bus.glob("*.kbp.yaml")):
        text = path.read_text(encoding="utf-8")
        identity = bundled.header(text)
        if identity is None:
            files.append({"name": path.name, "id": "", "version": "", "text": text})
            continue
        entry: dict[str, Any] = {
            "name": path.name,
            "id": identity[0],
            "version": identity[1],
        }
        if (
            identity not in index
            or index[identity].path.read_text(encoding="utf-8") != text
        ):
            entry["text"] = text
        files.append(entry)
    return files


def arguments(
    file: Path,
    *,
    root: Path | None = None,
    role: str | None = None,
    filing_values: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """kb reads each `.knowledge-bus/` folder from the root down to the file's folder. kb never reads
    the file itself, so the file may be missing. Raise UsageFault when the file's folder does not
    exist or the file is outside `root`. Raise ToolFault when the document-types file is not valid
    YAML. Raise InstallFault when kb needs the bundled universe specs and the bundled files are
    incomplete.
    """
    command = shlex.join(
        [
            "kb",
            "type",
            str(file),
            *(["--root", str(root)] if root else []),
            *(["--role", role] if role else []),
        ]
    )
    # os.path.abspath removes `..` parts, which Path.absolute keeps, so the root walk climbs the
    # actual parent folders.
    file = Path(os.path.abspath(file))
    folder = file.parent
    if not folder.is_dir():
        msg = f"folder {folder} does not exist."
        raise UsageFault(msg, "Run kb type --help for the flags.")
    root = Path(os.path.abspath(root)) if root is not None else root_folder(folder)
    try:
        folders = list(folder.relative_to(root).parts)
    except ValueError:
        msg = f"{file} is outside {root}, the folder given with --root."
        raise UsageFault(
            msg, "Pass a --root folder that holds the file, or drop --root."
        ) from None
    index = bundled.index()
    specs: list[dict[str, Any]] = []
    inventory: list[dict[str, str]] = []
    excluded = {
        ".knowledge-bus",
        ".obsidian",
        ".git",
        "node_modules",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
    for current, directories, names in os.walk(root, followlinks=False):
        knowledge_bus = Path(current) / KNOWLEDGE_BUS
        if KNOWLEDGE_BUS in directories:
            files = _spec_files(knowledge_bus, index)
            relative = Path(current).relative_to(root).as_posix()
            scope: dict[str, Any] = {
                "folder": "" if relative == "." else relative,
                "files": files,
            }
            workspace = knowledge_bus / "workspace.yaml"
            if workspace.is_file():
                scope["workspace_yaml"] = workspace.read_text(encoding="utf-8")
            specs.append(scope)
        directories[:] = sorted(
            d
            for d in directories
            if d not in excluded and not (Path(current) / d).is_symlink()
        )
        inventory.extend(
            {"path": (Path(current) / n).relative_to(root).as_posix()}
            for n in sorted(names)
        )
    if not any(scope["files"] or "workspace_yaml" in scope for scope in specs):
        # With no spec file or workspace.yaml from the root down, kb uses the bundled universe
        # specs, so fail now if they are missing.
        bundled.require()
    sent: dict[str, Any] = {
        "location": str(file),
        "name": file.name,
        "folders": folders,
        "knowledge_bus_folders": specs,
        "listing": inventory,
    }
    # knowledge-mcp 0.2.1 and earlier wrote record.yaml instead of document-types.yaml.
    # kb type writes neither file.
    for place in (records.PLACE, records.OLD_PLACE):
        saved = root / place
        if saved.is_file():
            sent["record"] = _record_text(saved, command)
            break
    sent["conventions_files"] = _convention_files(root, specs)
    sent.update({"filing_values": filing_values} if filing_values is not None else {})
    if role:
        sent["role"] = role
    return sent


def _convention_files(root: Path, specs: list[dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    for scope in specs:
        config = root / scope["folder"] / conventions.PLACE
        text = config.read_text(encoding="utf-8") if config.is_file() else ""
        if config.is_file() and not text.strip():
            raise ToolFault(
                problems.Error(
                    f"Save valid conventions YAML in {config}.",
                    code="conventions-invalid",
                ).details(),
                "Save a complete conventions file, then repeat kb type.",
            )
        result.append(dict(folder=scope["folder"], text=text))
    return result


def _record_text(saved: Path, command: str) -> str:
    text = saved.read_text(encoding="utf-8")
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        line = mark.line + 1 if mark is not None else 1
        detail = getattr(error, "problem", str(error))
        message = f"{saved} is not valid YAML: line {line}: {detail}."
        raise ToolFault(
            problems.Error(message, code="record-invalid").details(),
            f"Fix line {line}, then run {command} again.",
        ) from None
    return text


def type_catalog(
    file: Path, root: Path | None, role: str | None
) -> dict[tuple[str, str], dict[str, Any]]:
    """Map each (universe spec id, document type) pair to its `kb kbp kinds` entry."""
    sent = arguments(file, root=root, role=role)
    listing, _ = listed_kinds(
        Workspace(),
        ScopeRequest(
            folders=sent["folders"],
            knowledge_bus_folders=[
                KnowledgeBusFolder.model_validate(folder)
                for folder in sent["knowledge_bus_folders"]
                if not folder["folder"]
                or "/".join([*sent["folders"], sent["name"]]).startswith(
                    folder["folder"] + "/"
                )
            ],
        ),
    )
    return {
        (group["universe_spec"]["id"], item["kind"]): item
        for group in listing.get("universe_specs", [listing])
        for item in group["kinds"]
    }


def document_type(
    file: Path,
    *,
    root: Path | None = None,
    role: str | None = None,
    filing_values: list[dict[str, Any]] | None = None,
) -> tuple[str, bool]:
    """Append the kb_get_document_type answer to `log.jsonl`. Return the JSON answer and failure flag."""
    sent = arguments(file, root=root, role=role, filing_values=filing_values)
    server = build_server()

    async def call() -> Any:
        return await server.call_tool("kb_get_document_type", sent)

    result = anyio.run(call)
    text = json.dumps(result.structured_content, ensure_ascii=False)
    return text, bool(result.is_error)
