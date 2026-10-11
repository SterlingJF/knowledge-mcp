"""The element questions an outside document's passages are marked against, from `kbp` output.

Each universe spec in scope comes from `kbp --kinds`, and each document type's element questions
from its card, `kbp --card <kind> --universe <id> --format json` (`knowledge-bus/card/1`), in the
card's order. A section the card marks `links` belongs to the document types named in its
`kept_in`, whose own cards list the element, so a passage that settles the element is marked
for the document type that keeps the element.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "knowledge-mcp/mark/1"
CARD = "knowledge-bus/card/1"


class MarkError(ValueError):
    """The answer can't be given; the message says what to send instead."""


def pairs(listing: dict[str, Any]) -> list[tuple[str, str]]:
    """(universe spec id, document type id) for every document type in a `--kinds` listing."""
    return [
        (group["universe_spec"]["id"], kind["kind"])
        for group in listing.get("universe_specs", [listing])
        for kind in group["kinds"]
    ]


def elements(card: dict[str, Any]) -> list[dict[str, Any]]:
    """The sections a card's document type keeps: element id, question and strength."""
    if card.get("schema") != CARD:
        msg = (
            f"kbp --card printed schema {card.get('schema')!r}; knowledge-mcp reads {CARD}. "
            "The knowledge-bus pin and knowledge-mcp are out of step."
        )
        raise MarkError(msg)
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
) -> dict[str, list[dict[str, Any]]]:
    """Per universe spec id: each document type in kbp's order, with the elements it keeps."""
    found: dict[str, list[dict[str, Any]]] = {}
    for group in listing.get("universe_specs", [listing]):
        spec = group["universe_spec"]["id"]
        found[spec] = [
            {
                "kind": kind["kind"],
                "name": kind["name"],
                "action": kind.get("action"),
                "actor": kind.get("actor"),
                "elements": elements(cards[spec, kind["kind"]]),
            }
            for kind in group["kinds"]
        ]
    return found
