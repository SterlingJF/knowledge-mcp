"""Load the JSON Schemas that `just generate_contract_types` bundles into `schemas_auto/`."""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

# kbp_* tools return kbp's output with no output schema.
RESULTS = {
    "kb_list_convention_templates": "convention-templates",
    "kb_list_conventions": "folder-conventions",
    "kb_prepare_conventions": "conventions-update",
    "kb_prepare_document_move": "document-move",
    "kb_prepare_document_moves": "document-moves",
    "kb_get_document_type": "document-type",
    "kb_list_audiences": "audiences",
    "kb_prepare_import": "import",
    "kb_prepare_document_types": "document-types-update",
    "kb_record_edit": "edit",
    "kb_list_edits": "edits",
}


@cache
def bundle(name: str) -> dict[str, Any]:
    """Load `schemas_auto/<name>.schema.yaml`, which holds the schema and every schema it references."""
    place = resources.files("knowledge_mcp") / "schemas_auto" / f"{name}.schema.yaml"

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    loaded: dict[str, Any] = yaml.load(place.read_text(encoding="utf-8"), Loader=loader)
    return loaded


def _without_dialect(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: _without_dialect(value)
            for key, value in node.items()
            if key != "$schema"
        }
    if isinstance(node, list):
        return [_without_dialect(item) for item in node]
    return node


def listed(name: str) -> dict[str, Any]:
    """The bundle without `$schema` keys, as `tools/list` sends it."""
    # MCP reads a schema without `$schema` as 2020-12. Clients that compile schemas with
    # draft-07 Ajv reject the 2020-12 `$schema` URI.
    found: dict[str, Any] = _without_dialect(bundle(name))
    return found


def title(code: str) -> str:
    """Raise KeyError for an unknown code."""
    for item in bundle("problem")["properties"]["type"]["oneOf"]:
        if str(item["const"]).rsplit("/", 1)[-1] == code:
            return str(item["title"])
    msg = f"problem.schema.yaml lists no problem type {code}"
    raise KeyError(msg)


@cache
def _document_types() -> Draft202012Validator:
    return Draft202012Validator(listed("document-types"))


def record_issues(data: Any) -> list[str]:
    """Schema errors in document-types data as `<path>: <message>`, sorted by path."""
    issues = []
    for error in sorted(
        _document_types().iter_errors(data), key=lambda e: list(e.path)
    ):
        best = best_match([error]) or error
        place = "/".join(str(part) for part in best.absolute_path) or "the file"
        issues.append(f"{place}: {best.message}")
    return issues


def convention_issues(data: Any) -> list[str]:
    return [
        f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
        for e in Draft202012Validator(listed("conventions")).iter_errors(data)
    ]
