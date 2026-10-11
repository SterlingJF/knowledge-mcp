"""knowledge-mcp's own matching: a file's name and nearest folder against the document types in scope.

The words of the file name and of the folder holding it are matched against each document
type's other names (`alias.form` in `kbp --kinds`). A word in the universe spec's own label or
id names the whole universe spec, so it picks none of its document types. Each candidate says
whether a word of the file name matched, or only the folder. The hat orders the candidates; it
removes none. When no candidate matched on the file name, the answer also lists every document
type in scope, universe specs whose label or `covers` share a word with the path first.
"""

from __future__ import annotations

import re
from typing import Any

SCHEMA = "knowledge-mcp/fit/1"

# Words too general to tell document types apart, and file extensions. A folder named `docs` or
# `notes`, or a file name such as `0001-use-dolt.md`, says nothing about its document type.
STOPWORDS = frozenset(
    {
        *("a", "an", "and", "another", "any", "at", "by", "each", "for", "from", "in"),
        *("into", "it", "its", "of", "on", "one", "or", "other", "the", "to", "with"),
        *("md", "mdx", "txt", "rst", "adoc", "yml", "yaml", "json", "toml", "html"),
        *("file", "folder", "page", "site", "root", "sub", "level"),
        *("doc", "note", "use"),
    }
)


def stem(word: str) -> str:
    """The singular of a plain English plural; other words as they are."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def words(text: str | None) -> set[str]:
    """Lower-case words of two or more letters, split at case changes and separators."""
    if not text:
        return set()
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    found = set()
    for raw in re.split(r"[^A-Za-z0-9]+", spaced):
        word = raw.lower()
        if len(word) >= 2 and not word.isdigit():
            found.add(stem(word))
    return found


def _significant(text: str | None) -> set[str]:
    return words(text) - STOPWORDS


def _stem_of(name: str) -> str:
    """The file name without its extensions; a leading dot stays part of the name."""
    head, dot, _ = name[1:].partition(".")
    return name[0] + head if dot and name else name


def _groups(listing: dict[str, Any]) -> list[dict[str, Any]]:
    if "universe_specs" in listing:
        return list(listing["universe_specs"])
    return [listing]


def answer(
    listing: dict[str, Any],
    *,
    location: str,
    name: str,
    folders: list[str],
    hat: str | None,
    universe_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    """The fit answer for a `kinds/1` or `kinds-set/1` listing."""
    own = _significant(_stem_of(name))
    near = _significant(folders[-1]) if folders else set()
    path = own | near | set().union(*(_significant(folder) for folder in folders))
    wanted = _significant(hat)

    ranked = []
    for group in _groups(listing):
        spec = group["universe_spec"]
        whole = words(spec["id"]) | words(spec.get("label"))
        for kind in group["kinds"]:
            others = _significant((kind.get("alias") or {}).get("form")) - whole
            matched = (own | near) & others
            if not matched:
                continue
            candidate = {
                "universe_spec": spec["id"],
                "kind": kind["kind"],
                "name": kind["name"],
                "alias": kind["alias"],
                "action": kind["action"],
                "actor": kind["actor"],
                "timing": kind["timing"],
                "matched": sorted(matched),
                "matched_on": "name" if own & others else "folder",
            }
            fits_hat = bool(wanted & _significant(kind["actor"]))
            if hat is not None:
                candidate["hat_matches"] = fits_hat
            ranked.append(
                ((not fits_hat, -len(own & others), -len(matched)), candidate)
            )
    # Stable: equal ranks keep kbp's order of universe specs and document types.
    ranked.sort(key=lambda pair: pair[0])

    named = any(candidate["matched_on"] == "name" for _, candidate in ranked)
    return {
        "schema": SCHEMA,
        "location": location,
        "universe_specs": universe_specs,
        "candidates": [candidate for _, candidate in ranked],
        "every_document_type": None if named else every(listing, path),
    }


def every(
    listing: dict[str, Any], path: set[str] | None = None
) -> list[dict[str, Any]]:
    """Every document type in scope, universe specs whose label or `covers` share a path word first."""
    found = []
    for group in _groups(listing):
        spec = group["universe_spec"]
        shared = (path or set()) & (
            _significant(spec.get("label")) | _significant(spec.get("covers"))
        )
        found.append(
            {
                "universe_spec": spec["id"],
                "covers": spec.get("covers"),
                "covers_matched": sorted(shared),
                "kinds": [
                    {
                        "kind": kind["kind"],
                        "action": kind["action"],
                        "actor": kind["actor"],
                    }
                    for kind in group["kinds"]
                ],
            }
        )
    found.sort(key=lambda group: not group["covers_matched"])
    return found
