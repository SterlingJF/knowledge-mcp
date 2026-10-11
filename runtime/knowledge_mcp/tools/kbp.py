"""One tool per `kbp` mode; each returns what kbp prints, as is."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from knowledge_mcp import bundled, kbp, log
from knowledge_mcp.contract import (
    FOLDERS,
    LOCATION,
    UNIVERSE_SPECS,
    ScopeFolder,
    ScopeRequest,
)
from knowledge_mcp.scope import Rebuilt, ScopeError, Workspace
from knowledge_mcp.tools import respond

Location = Annotated[str, Field(description=LOCATION)]
Folders = Annotated[list[str], Field(description=FOLDERS)]
UniverseSpecs = Annotated[list[ScopeFolder], Field(description=UNIVERSE_SPECS)]
Universe = Annotated[
    str | None,
    Field(
        description="The id of one universe spec in scope, when several are in scope."
    ),
]

READS = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)

SCOPE_NOTE = (
    " kbp runs from the document's folder, rebuilt from what you send, so it uses the "
    "nearest `.knowledge-bus/` and the parent folder's universe specs named in "
    "`workspace.yaml`."
)


def note(rebuilt: Rebuilt, **extra: Any) -> dict[str, Any]:
    """Which files came from the bundled copies, and the digests of text sent in this call."""
    found: dict[str, Any] = {}
    if rebuilt.bundled:
        found["source"] = bundled.label()
        found["bundled"] = rebuilt.bundled
    if rebuilt.received:
        found["received"] = rebuilt.received
    return found | extra


def register(mcp: Any, workspace: Workspace) -> None:
    def scoped(
        tool: str,
        location: str,
        arguments: dict[str, Any],
        argv: list[str],
        *,
        sent_only: bool = False,
    ) -> CallToolResult:
        request = ScopeRequest.model_validate(
            {
                "folders": arguments["folders"],
                "universe_specs": arguments["universe_specs"],
            }
        )
        try:
            with workspace.rebuilt(request, sent_only=sent_only) as rebuilt:
                output = kbp.run(argv, rebuilt.cwd)
        except ScopeError as error:
            return respond.refusal(tool, location, arguments, str(error))
        return respond.printed(tool, location, arguments, output, note(rebuilt))

    @mcp.tool(
        name="kbp_check",
        title="Check universe specs",
        description=(
            "Check the universe specs in scope against the knowledge-bus protocol and return "
            "kbp's report as is. The check runs only on text you send: send each `*.kbp.yaml` "
            "file's text, or the digest an earlier answer returned." + SCOPE_NOTE
        ),
        annotations=READS,
    )
    def check(
        location: Location, folders: Folders, universe_specs: UniverseSpecs
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders, universe_specs=universe_specs, location=location
        )
        return scoped("kbp_check", location, arguments, [], sent_only=True)

    @mcp.tool(
        name="kbp_self_check",
        title="Check the protocol",
        description=(
            "Check the bundled knowledge-bus protocol against itself and return the "
            "`kbp --self-check` report as is."
        ),
        annotations=READS,
    )
    def self_check() -> CallToolResult:
        output = kbp.run(["--self-check"], Path.home())
        return respond.printed("kbp_self_check", "", {}, output)

    @mcp.tool(
        name="kbp_version",
        title="knowledge-bus version",
        description=(
            "Return the knowledge-bus release and protocol version that `kbp --version` prints."
        ),
        annotations=READS,
    )
    def version() -> CallToolResult:
        output = kbp.run(["--version"], Path.home())
        return respond.printed("kbp_version", "", {}, output)

    @mcp.tool(
        name="kbp_mint",
        title="Mint codes",
        description=(
            "Mint codes that collide with no code in the universe specs in scope, as "
            "`kbp --mint <kind> <count>` prints the codes." + SCOPE_NOTE
        ),
        annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    )
    def mint(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        kind: Annotated[
            Literal["element", "artifact", "frame", "factor"],
            Field(description="The kind of code to mint."),
        ],
        count: Annotated[
            int | None,
            Field(ge=1, le=100, description="The number of codes; 1 when left out."),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            universe_specs=universe_specs,
            location=location,
            kind=kind,
            count=count,
        )
        return scoped(
            "kbp_mint", location, arguments, ["--mint", kind, str(count or 1)]
        )

    @mcp.tool(
        name="kbp_inspect",
        title="Inspect universe specs",
        description=(
            "Return the JSON model `kbp --inspect` builds for a universe spec in scope and its "
            "guidance." + SCOPE_NOTE
        ),
        annotations=READS,
    )
    def inspect(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            universe_specs=universe_specs,
            location=location,
            universe=universe,
        )
        argv = ["--inspect", *(["--universe", universe] if universe else [])]
        return scoped("kbp_inspect", location, arguments, argv)

    @mcp.tool(
        name="kbp_explore",
        title="Write the Explorer",
        description=(
            "Write the offline Explorer for a universe spec in scope into knowledge-mcp's "
            "private folder, and return kbp's receipt and the folder's path. Open its "
            "`index.html` in a browser to browse the universe spec." + SCOPE_NOTE
        ),
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=False, open_world_hint=False
        ),
    )
    def explore(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            universe_specs=universe_specs,
            location=location,
            universe=universe,
        )
        request = ScopeRequest(folders=folders, universe_specs=universe_specs)
        try:
            with workspace.rebuilt(request) as rebuilt:
                output_dir = (
                    log.directory()
                    / "explorer"
                    / f"{rebuilt.key[:16]}-{universe or 'scope'}"
                )
                output_dir.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                argv = [
                    "--explore",
                    *(["--universe", universe] if universe else []),
                    "--output",
                    str(output_dir),
                    "--replace",
                ]
                output = kbp.run(
                    argv,
                    rebuilt.cwd,
                    KNOWLEDGE_BUS_EXPLORER_BUNDLE=str(
                        bundled.EXPLORER / "explorer-viewer.js"
                    ),
                    KNOWLEDGE_BUS_EXPLORER_BUNDLE_MANIFEST=str(
                        bundled.EXPLORER / "explorer-viewer.json"
                    ),
                )
        except ScopeError as error:
            return respond.refusal("kbp_explore", location, arguments, str(error))
        written = {"explorer": str(output_dir)} if output.code == 0 else {}
        return respond.printed(
            "kbp_explore", location, arguments, output, note(rebuilt, **written)
        )

    @mcp.tool(
        name="kbp_kinds",
        title="List document types",
        description=(
            "List every document type in scope as `kbp --kinds` prints the list: `kinds/1` for "
            "one universe spec, `kinds-set/1` for several." + SCOPE_NOTE
        ),
        annotations=READS,
    )
    def kinds(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        universe: Universe = None,
        format: Annotated[
            Literal["json", "markdown"] | None,
            Field(description="`json` when left out."),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            universe_specs=universe_specs,
            location=location,
            universe=universe,
            format=format,
        )
        argv = [
            "--kinds",
            *(["--universe", universe] if universe else []),
            *(["--format", format] if format else []),
        ]
        return scoped("kbp_kinds", location, arguments, argv)

    @mcp.tool(
        name="kbp_card",
        title="Read a card",
        description=(
            "Return the card for one document type as `kbp --card <kind> --format markdown` "
            'prints the card: sections, guidance, conditions and their "Depends on: …" lines. '
            "Read the card before writing the document." + SCOPE_NOTE
        ),
        annotations=READS,
    )
    def card(
        location: Location,
        folders: Folders,
        universe_specs: UniverseSpecs,
        kind: Annotated[
            str, Field(description="The document type id, such as `design-doc`.")
        ],
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            universe_specs=universe_specs,
            location=location,
            kind=kind,
            universe=universe,
        )
        argv = [
            "--card",
            kind,
            *(["--universe", universe] if universe else []),
            "--format",
            "markdown",
        ]
        return scoped("kbp_card", location, arguments, argv)
