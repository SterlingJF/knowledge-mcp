"""`kb_audience`: the choices a card's own universe spec names for who a document is for."""

from __future__ import annotations

import json
from typing import Annotated, Any

from mcp.types import CallToolResult, TextContent
from pydantic import Field

from knowledge_mcp import audience, kbp
from knowledge_mcp.contract import ScopeRequest
from knowledge_mcp.scope import SENT, ScopeError, Workspace
from knowledge_mcp.tools import respond
from knowledge_mcp.tools.kbp import READS, Folders, Location, Universe, UniverseSpecs

DESCRIPTION = """\
Return who a document of one type can be for, from the document type's own universe spec. When \
the universe spec declares an `audience` frame, `choices` holds its values, as `kbp --inspect` \
reports them; otherwise `choices` is empty and `actor` names who uses the document type. Send \
the same `location`, `folders` and `universe_specs` as `kb_fit`, and the document type id. When \
you can't tell who the document is for, ask the person and offer only these choices; with no \
choices, write for the `actor`.\
"""


def register(mcp: Any, workspace: Workspace) -> None:
    @mcp.tool(
        name="kb_audience",
        title="Who is this document for?",
        description=DESCRIPTION,
        annotations=READS,
    )
    def kb_audience(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        kind: Annotated[
            str, Field(description="The document type id, such as `design-doc`.")
        ],
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            location=location,
            folders=folders,
            universe_specs=universe_specs,
            kind=kind,
            universe=universe,
        )
        request = ScopeRequest(folders=folders, universe_specs=universe_specs)
        try:
            with workspace.rebuilt(request) as rebuilt:
                listed = kbp.run(["--kinds"], rebuilt.cwd)
                if listed.code != 0:
                    return respond.printed("kb_audience", location, arguments, listed)
                spec, item = audience.holder(json.loads(listed.stdout), kind, universe)
                inspected = kbp.run(
                    ["--inspect", "--universe", spec["id"]], rebuilt.cwd
                )
                if inspected.code != 0:
                    return respond.printed(
                        "kb_audience", location, arguments, inspected
                    )
                declared, choices = audience.frame(json.loads(inspected.stdout))
        except (ScopeError, audience.AudienceError) as error:
            return respond.refusal("kb_audience", location, arguments, str(error))

        result = {
            "schema": audience.SCHEMA,
            "location": location,
            "universe_spec": {
                "id": spec["id"],
                "version": spec["version"],
                "source": rebuilt.sources.get(spec["id"], SENT),
            },
            "kind": kind,
            "actor": item["actor"],
            "frame": declared,
            "choices": choices,
            "received": rebuilt.received,
        }
        return respond.answer(
            "kb_audience",
            location,
            arguments,
            [TextContent(type="text", text=respond.compact(result))],
        )
