from __future__ import annotations

import posixpath
import re
from collections import Counter
from typing import Any

from knowledge_mcp import document_types as records
from knowledge_mcp.models import FileChange, ListedFile
from knowledge_mcp.scope import Workspace
from knowledge_mcp.type_scope import Scopes


def inventory(
    workspace: Workspace,
    location: str,
    listing: list[ListedFile] | None,
    changes: list[FileChange] | None,
) -> list[ListedFile] | None:
    current = listing if listing is not None else workspace.inventories.get(location)
    if current is None:
        return None
    found = {records.normal_path(item.path): item for item in current}
    for change in changes or []:
        event, path, old, fingerprint = records.event(change)
        if old:
            found.pop(old, None)
        if event == "deleted":
            found.pop(path, None)
        else:
            found[path] = ListedFile(
                path=path, **({"fingerprint": fingerprint} if fingerprint else {})
            )
    result = [found[p] for p in sorted(found)]
    workspace.inventories[location] = result
    return result


def choices(answer: dict[str, Any]) -> list[tuple[str | None, str | None]]:
    if answer.get("recorded"):
        entry = answer["recorded"]["entry"]
        return [(entry.get("universe_spec"), entry.get("document_type"))]
    selected = {(c["universe_spec"], c["document_type"]) for c in answer["candidates"]}
    selected.update(
        (g["universe_spec"], k["document_type"])
        for g in answer["every_document_type"] or []
        for k in g["kinds"]
    )
    return sorted(selected) or [(None, None)]


def _style(path: str) -> str:
    stem = posixpath.splitext(posixpath.basename(path))[0]
    for separator, name in [("-", "lower-kebab"), ("_", "lower-snake")]:
        if re.fullmatch(r"[a-z0-9]+(?:" + re.escape(separator) + r"[a-z0-9]+)+", stem):
            return name
    return "unchanged"


def _name(path: str, peers: list[str]) -> tuple[str, str]:
    name = posixpath.basename(path)
    counts = Counter(_style(p) for p in peers)
    styles = sorted(
        ((counts[s], s) for s in ("lower-kebab", "lower-snake")), reverse=True
    )
    supported = [style for count, style in styles if count > 1]
    if not supported or styles[0][0] == styles[1][0]:
        return name, "unchanged"
    stem, ext = posixpath.splitext(name)
    if not re.fullmatch(r"[A-Za-z0-9 _-]+", stem) or not re.search(
        r"[A-Za-z0-9]", stem
    ):
        return name, "unchanged"
    stem = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", stem)
    stem = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", stem)
    words = re.split(r"[ _-]+", stem.strip(" _-"))
    style = styles[0][1]
    return ("-" if style == "lower-kebab" else "_").join(words).lower() + ext, style


def _untyped(result: dict[str, Any], path: str, files: records.Files) -> dict[str, Any]:
    result["status"] = (
        "no_document_type"
        if path in files and records.named(files[path])[2]
        else "document_type_needed"
    )
    return result


def _peers(
    path: str,
    type_id: tuple[str | None, str | None],
    files: records.Files,
    paths: set[str],
    scopes: Scopes,
) -> tuple[list[str], bool]:
    universe, kind = type_id
    subject_specs = frozenset(scopes.kinds_at(path))
    known_folders = {"" if f.folder == "." else f.folder for f in scopes.folders}
    missing = {
        p.split("/.knowledge-bus/")[0] if "/.knowledge-bus/" in p else ""
        for p in paths
        if ".knowledge-bus" in p.split("/")
    } - known_folders
    peers = []
    for peer in sorted(paths & files.keys() - {path}):
        if records.named(files[peer])[:2] != (universe, kind):
            continue
        if any(not f or peer.startswith(f + "/") for f in missing):
            return [], True
        if frozenset(scopes.kinds_at(peer)) == subject_specs and (
            scopes.conventions is None
            or scopes.conventions.context is None
            or all(
                scopes.same_definition(path, peer, identity)
                for identity in subject_specs
            )
        ):
            peers.append(peer)
    return peers, False


def assess(
    path: str,
    type_id: tuple[str | None, str | None],
    files: records.Files,
    *,
    listing: list[ListedFile] | None,
    scopes: Scopes,
) -> dict[str, Any]:
    universe, kind = type_id
    result: dict[str, Any] = dict(
        path=path,
        universe_spec=universe,
        document_type=kind,
        status="no_peers",
        proposal=None,
    )
    scopes.validate_conventions(path)
    if universe is None or kind is None:
        return _untyped(result, path, files)
    if scopes.conventions is not None:
        assessed = scopes.conventions.assess(result, listing)
        if assessed is not None:
            return assessed
    if listing is None:
        result["status"] = "listing_needed"
        return result
    paths = {records.normal_path(item.path) for item in listing}
    peers, incomplete = _peers(path, type_id, files, paths, scopes)
    if incomplete:
        result["status"] = "evidence_incomplete"
        return result
    if not peers:
        return result
    return _proposal(result, peers, paths, scopes)


def _proposal(
    result: dict[str, Any], peers: list[str], paths: set[str], scopes: Scopes
) -> dict[str, Any]:
    path = result["path"]
    universe, kind = result["universe_spec"], result["document_type"]
    current = posixpath.dirname(path)
    counts = Counter(posixpath.dirname(p) for p in peers)
    maximum = max(counts.values())
    tied = [f for f, n in counts.items() if n == maximum]

    def shared(folder: str) -> int:
        common = posixpath.commonpath([current, folder]) if current and folder else ""
        return len(common.split("/")) if common else 0

    folder = (
        current if current in tied else sorted(tied, key=lambda f: (-shared(f), f))[0]
    )
    evidence = [p for p in peers if posixpath.dirname(p) == folder]
    name, style = _name(path, evidence)
    destination = posixpath.join(folder, name)
    if (
        scopes.conventions is not None
        and scopes.conventions.context is not None
        and not scopes.allows_transfer(path, destination, (universe, kind))
    ):
        result["status"] = "destination_type_conflict"
    elif destination == path:
        result["status"] = "already_matches"
    elif destination in paths:
        result["status"] = "destination_occupied"
    else:
        result["status"] = "proposed"
        result["proposal"] = dict(
            folder=folder,
            name=name,
            path=destination,
            folder_new=False,
            name_style=style,
            evidence=evidence,
            folder_counts=[dict(folder=f, count=counts[f]) for f in sorted(counts)],
        )
    return result
