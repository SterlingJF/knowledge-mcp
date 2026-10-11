"""`kb fit <file>`: the terminal is the host, so this module reads what an agent would send.

It reads the file's folder chain and each `.knowledge-bus/` on the chain, builds the `kb_fit`
arguments the way an agent builds them, and calls the `kb_fit` tool of an in-process server.
It never reads the file itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio

from knowledge_mcp import bundled
from knowledge_mcp import record as records

KNOWLEDGE_BUS = ".knowledge-bus"


def top_folder(folder: Path) -> Path:
    """The knowledge base's top folder for a file in `folder`.

    The highest folder from `folder` up that holds a `.knowledge-bus/`; without one, the nearest
    folder holding `.git`, else the folder above `folder`, so the folder holding the file still
    counts in the match.
    """
    chain = (folder, *folder.parents)
    found = [candidate for candidate in chain if (candidate / KNOWLEDGE_BUS).is_dir()]
    if found:
        return found[-1]
    for candidate in chain:
        if (candidate / ".git").exists():
            return candidate
    return folder.parent


def arguments(
    file: Path, *, top: Path | None = None, hat: str | None = None
) -> dict[str, Any]:
    """The `kb_fit` arguments for `file`, read from the folders on its chain."""
    file = file.absolute()
    folder = file.parent
    if not folder.is_dir():
        msg = f"{folder} is not a folder."
        raise ValueError(msg)
    top = (top or top_folder(folder)).absolute()
    try:
        folders = list(folder.relative_to(top).parts)
    except ValueError:
        msg = f"{file} is not inside {top}."
        raise ValueError(msg) from None
    index = bundled.index()
    specs: list[dict[str, Any]] = []
    for depth in range(len(folders) + 1):
        knowledge_bus = top.joinpath(*folders[:depth], KNOWLEDGE_BUS)
        if not knowledge_bus.is_dir():
            continue
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
            if identity not in index:
                entry["text"] = text
            files.append(entry)
        scope: dict[str, Any] = {"depth": depth, "files": files}
        workspace = knowledge_bus / "workspace.yaml"
        if workspace.is_file():
            scope["workspace_yaml"] = workspace.read_text(encoding="utf-8")
        specs.append(scope)
    sent: dict[str, Any] = {
        "location": str(file),
        "name": file.name,
        "folders": folders,
        "universe_specs": specs,
    }
    record = top / records.PLACE
    if record.is_file():
        sent["record"] = record.read_text(encoding="utf-8")
    if hat:
        sent["hat"] = hat
    return sent


def fit(
    file: Path, *, top: Path | None = None, hat: str | None = None
) -> tuple[str, bool]:
    """The `kb_fit` answer's text for `file`, and whether it is a refusal."""
    from knowledge_mcp.main import build_server

    sent = arguments(file, top=top, hat=hat)
    server = build_server()

    async def call() -> Any:
        return await server.call_tool("kb_fit", sent)

    result = anyio.run(call)
    text = "\n".join(block.text for block in result.content if hasattr(block, "text"))
    return text, bool(result.is_error)
