"""`kb_fit`: what a file is for, from the universe specs in scope."""

from __future__ import annotations

import json
from typing import Annotated, Any

from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from knowledge_mcp import fit, kbp
from knowledge_mcp import record as records
from knowledge_mcp.contract import FileChange, ScopeRequest
from knowledge_mcp.scope import SENT, Rebuilt, ScopeError, Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import Folders, Location, UniverseSpecs

DESCRIPTION = """\
Say what a file is for: every fitting universe spec and document type, as a list. Works for a \
file in any source you can read, such as a local folder, Drive or Notion; knowledge-mcp opens no \
file. Send the file's name, its location as text, the folders from the knowledge base's top \
folder down to the file, and the universe specs in scope: each folder on that chain holding a \
`.knowledge-bus/`, empty ones included, with each `*.kbp.yaml` header's id and version and the \
text of any `workspace.yaml`. Leave out `.knowledge-bus/plugins/`, where plugins such as \
knowledge-mcp keep their files. When no folder on the chain holds a definition, the bundled \
universe specs apply. For a header matching a bundled universe spec, send the header \
alone; send any other file's text once per session, then the digest the answer returns.

Settle the fit in this order. Path: the answer's `universe_specs`. Document type: the \
`candidates`, matched on the file name and the folder holding the file; `matched_on` says \
"name" or "folder", and a folder match alone is weak. When no candidate matched on the name, \
`every_document_type` lists each document type in scope: weigh the candidates against that list, \
the outline and the conversation, or answer "no fit". Hat, the role of the person you work for, \
such as maintainer or product lead: send it as `hat` when you can tell, and candidates whose \
`actor` shares a word with the hat come first. `hat_matches` is that word match alone, so check \
each `actor` yourself; when no candidate matches, treat the hat as unsettled. Ask the person \
only when these steps leave more than one fit. When you can't tell the hat, state your guess and \
confirm it before the work starts. Then read the card with `kbp_card`.

When the knowledge base has a fit record, `.knowledge-bus/plugins/knowledge-mcp/record.yaml` \
in the top folder, send its text as `record`: knowledge-mcp then answers a recorded file from the record, in `recorded`, labelled \
"from the record", including "no fit". In `changes`, send the files moved or deleted since the record was \
saved, in the shape `kb_fit_record` takes: knowledge-mcp applies them to the record for this \
answer and saves nothing.\
"""


RecordText = Annotated[
    str | None,
    Field(
        description=(
            f"The text of `{records.PLACE}` at the knowledge base's top folder, as read; an empty "
            "text when the file is missing. Send the text once per session, then its digest."
        ),
    ),
]
RecordDigest = Annotated[
    str | None,
    Field(
        description=(
            "The digest an earlier answer in this session returned for the record's text, while "
            "the file still holds that text."
        )
    ),
]


def kinds_of(listing: dict[str, Any]) -> records.Kinds:
    """Each universe spec in a `--kinds` listing: its version and document type ids."""
    return {
        group["universe_spec"]["id"]: (
            str(group["universe_spec"]["version"]),
            frozenset(kind["kind"] for kind in group["kinds"]),
        )
        for group in listing.get("universe_specs", [listing])
    }


def scope_specs(listing: dict[str, Any], rebuilt: Rebuilt) -> list[dict[str, Any]]:
    """The universe specs in a `--kinds` listing: id, version, source and `from_parent`."""
    groups = listing.get("universe_specs", [listing])
    parents = set(listing.get("from_parent", []))
    return [
        {
            "id": spec["id"],
            "version": spec["version"],
            "source": rebuilt.sources.get(spec["id"], SENT),
            "from_parent": spec["id"] in parents
            or (rebuilt.nearest is not None and spec["id"] not in rebuilt.nearest),
        }
        for spec in (group["universe_spec"] for group in groups)
    ]


def register(mcp: Any, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_fit",
        title="What is this file for?",
        description=DESCRIPTION,
        annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=True, open_world_hint=False
        ),
    )
    def kb_fit(
        location: Location,
        name: Annotated[
            str, Field(description="The file name, such as `0042-cache.md`.")
        ],
        folders: Folders,
        universe_specs: UniverseSpecs,
        hat: Annotated[
            str | None,
            Field(
                description="The role of the person you work for, when you can tell."
            ),
        ] = None,
        record: RecordText = None,
        record_digest: RecordDigest = None,
        changes: Annotated[
            list[FileChange] | None,
            Field(
                description=(
                    "Files moved or deleted since the record was saved, in the shape "
                    "`kb_fit_record` takes, sent with the record. "
                    "knowledge-mcp applies them to the record for this answer and saves nothing."
                )
            ),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            name=name,
            folders=folders,
            universe_specs=universe_specs,
            hat=hat,
            record=record,
            record_digest=record_digest,
            changes=changes,
        )
        request = ScopeRequest(folders=folders, universe_specs=universe_specs)
        files = None
        received = []
        try:
            if changes and record is None and record_digest is None:
                msg = "Send the record's text or digest with `changes`."
                raise records.RecordError(msg)
            if record is not None or record_digest is not None:
                text = records.received_text(record, record_digest, workspace.recall)
                files = records.parse(text)
                if record is not None:
                    received.append(
                        {"name": records.PLACE, "digest": workspace.remember(text)}
                    )
            with workspace.rebuilt(request) as rebuilt:
                output = kbp.run(["--kinds"], rebuilt.cwd)
        except (ScopeError, records.RecordError) as error:
            return respond.refusal("kb_fit", location, arguments, str(error))
        if output.code != 0:
            return respond.printed("kb_fit", location, arguments, output)

        listing = json.loads(output.stdout)
        specs = scope_specs(listing, rebuilt)
        entry = None
        if files is not None and changes:
            # The asked file's scope stands for every path: only the asked file's entry is read.
            kinds = kinds_of(listing)
            files = records.merge(
                files,
                events=[change.event() for change in changes],
                fits=[],
                refit=False,
                kinds_at=lambda _path: kinds,
                allowed_by=None,
                fingerprints={},
            ).files
        if files is not None:
            key, entry = records.lookup(files, folders, name)
            in_scope = {spec["id"] for spec in specs}
            if entry is not None and not (
                entry.no_fit or entry.universe_spec in in_scope
            ):
                entry = None
        if entry is not None:
            result = {
                "schema": fit.SCHEMA,
                "location": location,
                "universe_specs": specs,
                "candidates": [],
                "every_document_type": None,
                "recorded": records.answer(key, entry),
            }
        else:
            result = fit.answer(
                listing,
                location=location,
                name=name,
                folders=folders,
                hat=hat,
                universe_specs=specs,
            )
        result["received"] = rebuilt.received + received
        text = respond.compact(result)
        return respond.answer(
            "kb_fit", location, arguments, [TextContent(type="text", text=text)]
        )
