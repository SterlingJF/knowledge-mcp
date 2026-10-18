"""Knowledge-base fixtures and harness arguments for document tools."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Awaitable, Callable
from functools import cache
from pathlib import Path
from typing import Any

import anyio
import yaml
from jsonschema import Draft202012Validator
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from referencing import Registry, Resource

MODULE = Path(__file__).resolve().parent.parent
BUNDLED = MODULE / "knowledge-bus" / "universes"
CONTRACTS = MODULE.parent / "contracts" / "extensions" / "mcp" / "v1"

CODEBASE = "codebase-recordkeeping"
PRODUCT = "product-development"

_HEADER = re.compile(r"^(universe|guidance):\s*$")
_FIELD = re.compile(r"^\s+(id|version):\s*(.+?)\s*$")


def header(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    inside = False
    for line in text.splitlines():
        if _HEADER.match(line):
            inside = True
            continue
        if inside and line and not line[0].isspace():
            break
        match = _FIELD.match(line) if inside else None
        if match:
            found[match.group(1)] = match.group(2).strip("'\"")
    return found


def knowledge_base(root: Path, scopes: dict[str, list[str]]) -> Path:
    """An empty list creates an empty .knowledge-bus/ folder."""
    for folder, ids in scopes.items():
        target = root / folder / ".knowledge-bus"
        target.mkdir(parents=True, exist_ok=True)
        for universe_id in ids:
            for source in sorted((BUNDLED / universe_id).glob("*.kbp.yaml")):
                name = source.name.replace("universe.kbp.yaml", "kbp.yaml")
                (target / f"{universe_id}.{name}").write_text(source.read_text())
    return root


def write(root: Path, relative: str, text: str = "") -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def scope_arguments(
    root: Path, document: str, *, send_text: bool = False
) -> dict[str, Any]:
    parts = Path(document).parts
    folders = list(parts[:-1])
    specs: list[dict[str, Any]] = []
    for depth in range(len(folders) + 1):
        knowledge_bus = root.joinpath(*folders[:depth], ".knowledge-bus")
        if not knowledge_bus.is_dir():
            continue
        files = []
        for path in sorted(knowledge_bus.glob("*.kbp.yaml")):
            text = path.read_text()
            entry: dict[str, Any] = {"name": path.name, **header(text)}
            if send_text:
                entry["text"] = text
            files.append(entry)
        scope: dict[str, Any] = {"folder": "/".join(folders[:depth]), "files": files}
        workspace = knowledge_bus / "workspace.yaml"
        if workspace.is_file():
            scope["workspace_yaml"] = workspace.read_text()
        specs.append(scope)
    return {"folders": folders, "knowledge_bus_folders": specs}


def type_arguments(
    root: Path,
    document: str,
    *,
    send_text: bool = False,
    location: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    """The document path is relative to the knowledge base."""
    arguments = {
        "location": location or str(root / document),
        "name": Path(document).name,
        **scope_arguments(root, document, send_text=send_text),
    }
    if role is not None:
        arguments["role"] = role
    return arguments


def server_parameters(state: Path, **extra_env: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "knowledge_mcp"],
        cwd=MODULE,
        env={"XDG_STATE_HOME": str(state), "PATH": os.environ["PATH"], **extra_env},
    )


def session(
    parameters: StdioServerParameters,
    steps: Callable[[Client], Awaitable[Any]],
) -> Any:

    async def main() -> Any:
        async with Client(stdio_client(parameters), mode="legacy") as client:
            return await steps(client)

    return anyio.run(main)


def texts(result: Any) -> list[str]:
    return [block.text for block in result.content]


def fit(result: Any) -> dict[str, Any]:
    return checked(result, "document-type")


def checked(result: Any, contract: str) -> dict[str, Any]:
    assert not result.is_error, texts(result)
    [text] = texts(result)
    answer = json.loads(text)
    assert result.structured_content == answer
    validator(contract).validate(answer)
    return answer


@cache
def registry() -> Registry:
    """Register schemas by $id so references between schema files resolve."""
    resources = []
    for path in sorted(CONTRACTS.glob("*.schema.yaml")):
        schema = yaml.safe_load(path.read_text())
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@cache
def validator(contract: str) -> Draft202012Validator:
    schema = yaml.safe_load((CONTRACTS / f"{contract}.schema.yaml").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=registry())


def candidates(answer: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (item["universe_spec"], item["document_type"]) for item in answer["candidates"]
    ]


def listed(answer: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (group["universe_spec"], kind["document_type"])
        for group in answer["every_document_type"] or []
        for kind in group["kinds"]
    ]
