"""Read the audience choices of a universe spec from kbp output."""

from __future__ import annotations

from typing import Any

from knowledge_mcp import problems

SCHEMA = "knowledge-mcp/audiences/1"
AUDIENCE_ID = "audience"


class AudienceError(problems.Error):
    code = "document-type-unknown"


def holder(
    listing: dict[str, Any], kind: str, universe: str | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Find the universe spec and the entry for document type `kind` in a `kb kbp kinds` listing.

    `universe` limits the search to one universe spec. Raise AudienceError when no universe
    spec, or more than one, holds `kind`.
    """
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
            f"universe spec {universe}" if universe else "the universe specs that apply"
        )
        msg = f"No document type {kind!r} in {where}. Pick a document type from the `kbp_kinds` list."
        raise AudienceError(msg, pointer=problems.pointer("document_type"))
    if len(found) > 1:
        ids = ", ".join(spec["id"] for spec, _ in found)
        msg = (
            f"Document type {kind!r} is in universe specs {ids}. "
            "Send the id of the universe spec you mean as `universe_spec`."
        )
        raise AudienceError(
            msg, code="argument-invalid", pointer=problems.pointer("universe_spec")
        )
    return found[0]


def frame(model: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return the audience question and its choices from a `kb kbp inspect` model.

    With no audience question, return `(None, [])`.
    """
    entities = model.get("entities", [])
    declared = next(
        (
            e
            for e in entities
            if e.get("kind") == "frame" and e.get("sourceId") == AUDIENCE_ID
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
    return {"id": AUDIENCE_ID, "question": declared.get("description", "")}, choices
