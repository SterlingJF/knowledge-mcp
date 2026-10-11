"""Who a document is for, from the card's own universe spec, as `kbp` reports the spec.

The choices are the values of the universe spec's `audience` frame, read from the
`knowledge-bus/explorer-model/1` model that `kbp --inspect` prints. A universe spec that declares
no `audience` frame offers no choices; the document type's `actor` from `kbp --kinds` stands
instead.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "knowledge-mcp/audience/1"
MODEL = "knowledge-bus/explorer-model/1"
FRAME = "audience"


class AudienceError(ValueError):
    """The answer can't be given; the message says what to send instead."""


def holder(
    listing: dict[str, Any], kind: str, universe: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The universe spec in a `--kinds` listing that holds `kind`, and the document type."""
    groups = listing.get("universe_specs", [listing])
    found = [
        (group["universe_spec"], item)
        for group in groups
        for item in group["kinds"]
        if item["kind"] == kind
        and (universe is None or group["universe_spec"]["id"] == universe)
    ]
    if not found:
        where = (
            f"universe spec {universe}" if universe else "the universe specs in scope"
        )
        msg = f"No document type {kind!r} in {where}: pick one that `kbp_kinds` lists."
        raise AudienceError(msg)
    if len(found) > 1:
        ids = ", ".join(spec["id"] for spec, _ in found)
        msg = (
            f"Document type {kind!r} is in {ids}: send the one you mean as `universe`."
        )
        raise AudienceError(msg)
    return found[0]


def frame(model: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The `audience` frame and its values in a `kbp --inspect` model, or none."""
    if model.get("schema") != MODEL:
        msg = (
            f"kbp --inspect printed schema {model.get('schema')!r}; knowledge-mcp reads {MODEL}. "
            "The knowledge-bus pin and knowledge-mcp are out of step."
        )
        raise AudienceError(msg)
    entities = model.get("entities", [])
    declared = next(
        (
            e
            for e in entities
            if e.get("kind") == "frame" and e.get("sourceId") == FRAME
        ),
        None,
    )
    if declared is None:
        return None, []
    choices = []
    for entity in entities:
        if entity.get("kind") != "option" or entity.get("frameId") != declared["id"]:
            continue
        choice = {"id": entity["sourceId"], "label": entity["label"]}
        if entity.get("description"):
            choice["question"] = entity["description"]
        choices.append(choice)
    return {"id": FRAME, "question": declared.get("description", "")}, choices
