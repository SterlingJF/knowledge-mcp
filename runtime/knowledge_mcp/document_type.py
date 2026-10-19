"""Rank document types by alias words found in a file name or its nearest folder."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

WORD_MIN_LENGTH = 2

# `ies` becomes `y` after two or more letters, so `ties` becomes `tie`, not `ty`. A final `s`
# drops after three or more letters, except after `s`, `u` or `i`. `bus`, `class` and
# `analysis` stay.
IES_PLURAL = re.compile(r"(.{2,})ies")
S_PLURAL = re.compile(r"(.{2,}[^isu])s")

SCHEMA = "knowledge-mcp/document-type/1"

ROLE = "The reader's role, such as maintainer. Put document types for that role first."

# Ignore common words and extensions to avoid unrelated alias matches.
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
    if plural := IES_PLURAL.fullmatch(word):
        return plural[1] + "y"
    if plural := S_PLURAL.fullmatch(word):
        return plural[1]
    return word


def words(text: str | None) -> set[str]:
    if not text:
        return set()
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    found = set()
    for raw in re.split(r"[^A-Za-z0-9]+", spaced):
        word = raw.lower()
        if len(word) >= WORD_MIN_LENGTH and not word.isdigit():
            found.add(stem(word))
    return found


def _significant(text: str | None) -> set[str]:
    return words(text) - STOPWORDS


def _without_extensions(name: str) -> str:
    """Keep a leading dot, as in `.env`, as part of the name."""
    head, dot, _ = name[1:].partition(".")
    return name[0] + head if dot and name else name


def _groups(listing: dict[str, Any]) -> list[dict[str, Any]]:
    if "universe_specs" in listing:
        return list(listing["universe_specs"])
    return [listing]


@dataclass(frozen=True)
class MatchRequest:
    location: str
    name: str
    folders: list[str]
    role: str | None
    universe_specs: list[dict[str, Any]]


def answer(listing: dict[str, Any], sent: MatchRequest) -> dict[str, Any]:
    """`listing` is `kb kbp kinds` output, schema `knowledge-bus/kinds/1` or
    `knowledge-bus/kinds-set/1`. Ignore alias words shared with the universe spec id or
    label to avoid ranking by the universe spec name.
    The role changes the candidate order, never the candidate list. When no candidate matches the file
    name, `every_document_type` lists all document types.
    """
    location, name, folders, role, universe_specs = (
        sent.location,
        sent.name,
        sent.folders,
        sent.role,
        sent.universe_specs,
    )
    own = _significant(_without_extensions(name))
    near = _significant(folders[-1]) if folders else set()
    path = own | near | set().union(*(_significant(folder) for folder in folders))
    wanted = _significant(role)

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
                "document_type": kind["kind"],
                "name": kind["name"],
                "alias": kind["alias"],
                "action": kind["action"],
                "actor": kind["actor"],
                "timing": kind["timing"],
                "matched": sorted(matched),
                "matched_on": "name" if own & others else "folder",
            }
            role_matches = bool(wanted & _significant(kind["actor"]))
            if role is not None:
                candidate["role_matches"] = role_matches
            ranked.append(
                ((not role_matches, -len(own & others), -len(matched)), candidate)
            )
    # Python's sort is stable, so equal ranks keep the order kbp printed.
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
    """Put universe specs with word overlap between `path` and `label` or `covers` first."""
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
                        "document_type": kind["kind"],
                        "action": kind["action"],
                        "actor": kind["actor"],
                    }
                    for kind in group["kinds"]
                ],
            }
        )
    found.sort(key=lambda group: not group["covers_matched"])
    return found
