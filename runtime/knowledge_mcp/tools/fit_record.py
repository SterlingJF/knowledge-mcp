"""`kb_fit_record`: the fit record merged with the file changes and the fits, for the host to save."""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass, field
from typing import Annotated, Any

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from knowledge_mcp import fit, kbp
from knowledge_mcp import record as records
from knowledge_mcp.contract import (
    FileChange,
    FitItem,
    KnowledgeBusFolder,
    ListedFile,
    ScopeFolder,
    ScopeRequest,
)
from knowledge_mcp.edits import Basis
from knowledge_mcp.kbp import Printed
from knowledge_mcp.scope import ScopeError, Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.fit import RecordDigest, RecordText, kinds_of, scope_specs

DESCRIPTION = f"""\
Keep the fit record, `{records.PLACE}` in the knowledge base's top folder: which universe \
spec and document type each file is, or "no fit", and who the file is for. The record sits in \
knowledge-mcp's own plugin folder, `.knowledge-bus/plugins/knowledge-mcp/`; `kbp` reads no \
definition from `plugins/`. \
knowledge-mcp writes no file; you save the text the answer returns, creating the folders when \
missing.

Send the record as you read the file just now, the file changes since then, and every \
`.knowledge-bus/` folder of the knowledge base, its definitions only. Send the changes as \
`listing`, every file of the knowledge base outside `.knowledge-bus/`, which knowledge-mcp compares with the record you sent (on a session's \
first call), or as `changes`, the files created, deleted, moved or edited. The answer to a listing \
holds `listing_changes`, the changes the listing showed. A moved file keeps a corrected entry \
or a confirmed reader; deleted files leave the record, and a deleted correction comes back with \
a note. New files and moved plain fits come back in `to_settle` with the candidates `kb_fit` \
would give: settle each one, then send it in `fits` with `made` `fit`. Send a fit or reader \
the person states with `made` `correction`. A correction wins over any later fit. `refit` \
lists every file again for settling, corrections excepted.

Save only when the person asked in this session, or a standing line the person wrote covers \
keeping the record: send that ground as `basis`, `basis_text` and `basis_location`, and each \
saved entry names the ground. Without a ground, `record` comes back empty. When `record` holds \
text, read the file again right before writing: if the file still holds the text you sent, \
write the returned text at once. Otherwise send the new text with the same `changes` and \
`fits`, and in place of the listing send `listing_changes` added to `changes`; another chat's \
files would read as deleted or created against a listing taken before the other chat saved.\
"""


@dataclass
class Scope:
    """The universe specs in scope at a set of files, as `kbp --kinds` lists them."""

    index: int
    listing: dict[str, Any]
    specs: list[dict[str, Any]]
    kinds: records.Kinds
    wants_every: bool = False


class KbpFailed(Exception):
    def __init__(self, output: Printed) -> None:
        super().__init__(output.stderr)
        self.output = output


@dataclass
class Scopes:
    """The `.knowledge-bus/` folders a host sent, and the scope at each path, run once each."""

    workspace: Workspace
    folders: list[KnowledgeBusFolder]
    found: dict[tuple[tuple[str, ...], ...], Scope] = field(default_factory=dict)
    received: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        seen = set()
        for item in self.folders:
            parts = _parts(item.folder)
            if parts in seen:
                msg = f"Send each `.knowledge-bus/` folder once: {item.folder!r} came twice."
                raise ScopeError(msg)
            seen.add(parts)

    def at(self, path: str) -> Scope:
        chain = path.split("/")[:-1]
        applicable = sorted(
            (
                (_parts(item.folder), item)
                for item in self.folders
                if list(_parts(item.folder)) == chain[: len(_parts(item.folder))]
            ),
            key=lambda pair: len(pair[0]),
        )
        key = tuple(parts for parts, _ in applicable)
        if key in self.found:
            return self.found[key]
        deepest = list(applicable[-1][0]) if applicable else []
        request = ScopeRequest(
            folders=deepest,
            universe_specs=[
                ScopeFolder(
                    depth=len(parts),
                    files=item.files,
                    workspace_yaml=item.workspace_yaml,
                )
                for parts, item in applicable
            ],
        )
        with self.workspace.rebuilt(request) as rebuilt:
            output = kbp.run(["--kinds"], rebuilt.cwd)
            if output.code != 0:
                raise KbpFailed(output)
            listing = json.loads(output.stdout)
            specs = scope_specs(listing, rebuilt)
        for item in rebuilt.received:
            self.received[str(item["digest"])] = item
        scope = Scope(len(self.found), listing, specs, kinds_of(listing))
        self.found[key] = scope
        return scope

    def kinds_at(self, path: str) -> records.Kinds:
        return self.at(path).kinds


def _parts(folder: str) -> tuple[str, ...]:
    if folder in ("", "."):
        return ()
    return tuple(records.normal_path(folder).split("/"))


def _listing_events(
    files: records.Files, listing: list[ListedFile] | None
) -> list[records.Event] | None:
    """The changes a listing shows, against the record text the listing came with."""
    if listing is None:
        return None
    listed: dict[str, str | None] = {}
    for item in listing:
        path = records.normal_path(item.path)
        if not records.is_configuration(path):
            listed[path] = item.fingerprint
    return records.compare(files, listed)


def _change_events(changes: list[FileChange] | None) -> list[records.Event]:
    return [change.event() for change in changes or []]


def register(mcp: Any, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_fit_record",
        title="Keep the fit record",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=False, open_world_hint=False
        ),
    )
    def kb_fit_record(
        location: Annotated[
            str,
            Field(
                description=(
                    "The knowledge base's location as plain text: its top folder's local path, "
                    "a Drive folder link or a Notion page. knowledge-mcp opens nothing there."
                )
            ),
        ],
        record: RecordText = None,
        record_digest: RecordDigest = None,
        universe_specs: Annotated[
            list[KnowledgeBusFolder],
            Field(
                description=(
                    "Every folder of the knowledge base holding a `.knowledge-bus/`, empty ones "
                    "included, with each `*.kbp.yaml` header's id and version and the text of "
                    "any `workspace.yaml`: send a file's text once per session unless the header "
                    "matches a bundled universe spec. Leave out `plugins/`, the record's folder "
                    "included. When no folder on a file's chain holds a definition, the bundled "
                    "universe specs apply."
                )
            ),
        ] = [],  # noqa: B006 - pydantic copies the default for each call.
        listing: Annotated[
            list[ListedFile] | None,
            Field(
                description=(
                    "Every file of the knowledge base outside `.knowledge-bus/`, to compare with "
                    "the record on a session's first call."
                )
            ),
        ] = None,
        changes: Annotated[
            list[FileChange] | None,
            Field(
                description=(
                    "Files created, deleted, moved or edited since the record was read. On a "
                    "merge again after another chat saved, add the first answer's "
                    "`listing_changes` here in place of the listing."
                )
            ),
        ] = None,
        fits: Annotated[
            list[FitItem] | None,
            Field(
                description="Fits you settled, and fits or readers the person stated."
            ),
        ] = None,
        refit: Annotated[
            bool | None,
            Field(
                description="List every recorded file for settling again, corrections excepted."
            ),
        ] = None,
        basis: Annotated[
            Basis | None,
            Field(
                description=(
                    "`request`, `line` or `change_row`: what the person said that lets you save "
                    "the record."
                )
            ),
        ] = None,
        basis_text: Annotated[
            str | None, Field(description="The request, line or change row, quoted.")
        ] = None,
        basis_location: Annotated[
            str | None,
            Field(
                description="The file or place holding the line, such as `AGENTS.md`."
            ),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            record=record,
            record_digest=record_digest,
            universe_specs=universe_specs or None,
            listing=listing,
            changes=changes,
            fits=fits,
            refit=refit,
            basis=basis,
            basis_text=basis_text,
            basis_location=basis_location,
        )
        try:
            result = _merge(
                workspace,
                location=location,
                record=record,
                record_digest=record_digest,
                folders=universe_specs,
                listing=listing,
                changes=changes,
                fits=fits or [],
                refit=bool(refit),
                basis=basis,
                basis_text=basis_text,
                basis_location=basis_location,
            )
        except (records.RecordError, ScopeError) as error:
            return respond.refusal("kb_fit_record", location, arguments, str(error))
        except KbpFailed as failed:
            return respond.printed("kb_fit_record", location, arguments, failed.output)
        return respond.answer(
            "kb_fit_record",
            location,
            arguments,
            [TextContent(type="text", text=respond.compact(result))],
        )


def _merge(
    workspace: Workspace,
    *,
    location: str,
    record: str | None,
    record_digest: str | None,
    folders: list[KnowledgeBusFolder],
    listing: list[ListedFile] | None,
    changes: list[FileChange] | None,
    fits: list[FitItem],
    refit: bool,
    basis: Basis | None,
    basis_text: str | None,
    basis_location: str | None,
) -> dict[str, Any]:
    text = records.received_text(record, record_digest, workspace.recall)
    files = records.parse(text)
    based_on = workspace.remember(text)
    allowed_by = None
    if basis is not None:
        if not basis_text:
            msg = "Send `basis_text`, the request, line or change row quoted, with `basis`."
            raise records.RecordError(msg)
        allowed_by = records.AllowedBy(
            basis=basis, text=basis_text, location=basis_location
        )
    scopes = Scopes(workspace, folders)
    from_listing = _listing_events(files, listing)
    merged = records.merge(
        files,
        events=(from_listing or []) + _change_events(changes),
        fits=fits,
        refit=refit,
        kinds_at=scopes.kinds_at,
        allowed_by=allowed_by,
        fingerprints=workspace.fingerprints.setdefault(location, {}),
    )

    to_settle = []
    for waiting in merged.settle.values():
        scope = scopes.at(waiting.path)
        folder, name = posixpath.split(waiting.path)
        found = fit.answer(
            scope.listing,
            location=waiting.path,
            name=name,
            folders=folder.split("/") if folder else [],
            hat=None,
            universe_specs=scope.specs,
        )
        if found["every_document_type"] is not None:
            scope.wants_every = True
        item: dict[str, Any] = {
            "path": waiting.path,
            "scope": scope.index,
            "candidates": found["candidates"],
        }
        if waiting.old_path is not None:
            item["old_path"] = waiting.old_path
        if waiting.was is not None:
            item["was"] = waiting.was.plain()
        to_settle.append(item)

    changed = {path: entry.plain() for path, entry in merged.files.items()} != {
        path: entry.plain() for path, entry in files.items()
    }
    saved = None
    if changed and allowed_by is not None:
        saved = records.dump(merged.files)
        workspace.remember(saved)

    received = list(scopes.received.values())
    if record is not None:
        received.append({"name": records.PLACE, "digest": based_on})
    result: dict[str, Any] = {
        "schema": records.UPDATE,
        "location": location,
        "based_on": based_on,
        "record": saved,
        "digest": records.digest(saved) if saved is not None else None,
        "changed": merged.changed,
        "to_settle": to_settle,
        "scopes": [
            {
                "universe_specs": scope.specs,
                "every_document_type": fit.every(scope.listing)
                if scope.wants_every
                else None,
            }
            for scope in sorted(scopes.found.values(), key=lambda scope: scope.index)
        ],
        "received": received,
    }
    if from_listing is not None:
        result["listing_changes"] = [records.as_change(event) for event in from_listing]
    if changed and allowed_by is None:
        result["note"] = (
            "Nothing to save until the person asks, or a standing line the person wrote covers "
            "keeping the record: send that ground as `basis`."
        )
    return result
