"""Build the document types and questions for kb_prepare_import from kbp output."""

from __future__ import annotations

from typing import Any

SCHEMA = "knowledge-mcp/import/1"


def pairs(listing: dict[str, Any]) -> list[tuple[str, str]]:
    """Accept `kbp --kinds` output for one universe spec or several."""
    return [
        (group["universe_spec"]["id"], kind["kind"])
        for group in listing.get("universe_specs", [listing])
        for kind in group["kinds"]
    ]


def elements(card: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "element": section["element"],
            "question": section["question"],
            "strength": section["strength"],
        }
        for section in card["sections"]
        if section.get("mode") != "links"
    ]


def document_types(
    listing: dict[str, Any], cards: dict[tuple[str, str], dict[str, Any]]
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for group in listing.get("universe_specs", [listing]):
        spec = group["universe_spec"]["id"]
        found += [
            {
                "universe_spec": spec,
                "document_type": kind["kind"],
                "name": kind["name"],
                "action": kind.get("action"),
                "actor": kind.get("actor"),
                "elements": elements(cards[spec, kind["kind"]]),
            }
            for kind in group["kinds"]
        ]
    return found
