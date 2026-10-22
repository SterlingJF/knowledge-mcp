from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from knowledge_mcp import bundled, kbp, log
from knowledge_mcp.models import (
    KNOWLEDGE_BUS_FOLDERS,
    KnowledgeBusFolder,
    ScopeRequest,
)
from knowledge_mcp.scope import Rebuilt, Workspace
from knowledge_mcp.tools import respond

Location = Annotated[
    str,
    Field(
        description="A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location."
    ),
]
Folders = Annotated[
    list[str],
    Field(
        description='Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.'
    ),
]
KnowledgeBusFolders = Annotated[
    list[KnowledgeBusFolder], Field(description=KNOWLEDGE_BUS_FOLDERS)
]
Universe = Annotated[
    str | None,
    Field(
        description="Id of the universe spec to use when several universe specs apply."
    ),
]

# READS omits idempotent_hint because MCP defines that hint only for tools that change state.
READS = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def note(rebuilt: Rebuilt, **extra: Any) -> dict[str, Any]:
    found: dict[str, Any] = {}
    if rebuilt.bundled:
        found["source"] = bundled.label()
        found["bundled"] = rebuilt.bundled
    if rebuilt.received:
        found["received"] = rebuilt.received
    return found | extra


def register(mcp: MCPServer, workspace: Workspace) -> None:
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
                "knowledge_bus_folders": arguments.get("knowledge_bus_folders", []),
            }
        )
        with workspace.rebuilt(request, sent_only=sent_only) as rebuilt:
            output = kbp.run(argv, rebuilt.cwd)
        return respond.printed(tool, location, arguments, output, note(rebuilt))

    @mcp.tool(
        name="kbp_validate",
        title="Validate universe specs",
        description=(
            "Validate files in the nearest supplied `.knowledge-bus/` folder and parent files named in its `workspace.yaml`, using file text or digests from this session. Return kbp's report and exit code. Ignores bundled files. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def validate(
        location: Location, folders: Folders, knowledge_bus_folders: KnowledgeBusFolders
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            location=location,
        )
        return scoped("kbp_validate", location, arguments, [], sent_only=True)

    @mcp.tool(
        name="kbp_self_check",
        title="Validate the bundled protocol",
        description=(
            "Validate kbp's bundled protocol definition with `kbp --self-check`. Returns kbp's report and exit code. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def self_check() -> CallToolResult:
        output = kbp.run(["--self-check"], Path.home())
        return respond.printed("kbp_self_check", "", {}, output)

    @mcp.tool(
        name="kbp_version",
        title="Get the knowledge-bus version",
        description=(
            "Get the installed knowledge-bus release and protocol version from `kbp --version`. Returns kbp's text and exit code. Appends the result to `log.jsonl`."
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
            "Mint new `code` values of one `kind` for universe spec entries. Skips values already declared in the universe specs that apply and returns kbp's list and exit code. Writes no universe spec file, so add the returned values to the universe specs yourself. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def mint(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        kind: Literal["element", "artifact", "frame", "factor"],
        count: Annotated[
            int | None,
            Field(ge=1, le=100, description="Number of codes to mint, one by default."),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            location=location,
            kind=kind,
            count=count,
        )
        return scoped(
            "kbp_mint", location, arguments, ["--mint", kind, str(count or 1)]
        )

    @mcp.tool(
        name="kbp_inspect",
        title="Inspect a universe spec",
        description=(
            "Get a universe spec and its type guidance as kbp's JSON model. Returns the JSON and exit code. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def inspect(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            location=location,
            universe=universe,
        )
        argv = ["--inspect", *(["--universe", universe] if universe else [])]
        return scoped("kbp_inspect", location, arguments, argv)

    @mcp.tool(
        name="kbp_explore",
        title="Write a viewer",
        description=(
            "Write an offline HTML viewer for a universe spec under `explorer/` beside `log.jsonl`. Returns kbp's JSON summary, exit code and viewer folder path. Replaces the previous viewer when folder paths, file names, file order, file contents and `universe` are unchanged. Appends the result to `log.jsonl`."
        ),
        # `--replace` overwrites the earlier viewer in the same folder, so the tool is destructive.
        annotations=ToolAnnotations(
            read_only_hint=False, destructive_hint=True, open_world_hint=False
        ),
    )
    def explore(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        universe: Universe = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            location=location,
            universe=universe,
        )
        request = ScopeRequest(
            folders=folders, knowledge_bus_folders=knowledge_bus_folders
        )
        with workspace.rebuilt(request) as rebuilt:
            output_dir = (
                log.directory() / "explorer" / f"{rebuilt.key[:16]}-{universe or 'all'}"
            )
            output_dir.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            argv = [
                "--explore",
                *(["--universe", universe] if universe else []),
                "--output",
                str(output_dir),
                "--replace",
            ]
            output = kbp.run(argv, rebuilt.cwd)
        written = {"explorer": str(output_dir)} if output.code == 0 else {}
        return respond.printed(
            "kbp_explore", location, arguments, output, note(rebuilt, **written)
        )

    @mcp.tool(
        name="kbp_kinds",
        title="List document types",
        description=(
            "List the document types of the universe specs that apply. Returns kbp's list and exit code. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def kinds(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        universe: Universe = None,
        format: Annotated[
            Literal["json", "markdown"] | None,
            Field(description="Defaults to `json`."),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
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
            "Read the card for a document type before you draft or edit a document of that type. Returns kbp's card with purpose, writing advice and section questions as Markdown by default or native JSON, plus the exit code. Appends the result to `log.jsonl`."
        ),
        annotations=READS,
    )
    def card(
        location: Location,
        folders: Folders,
        knowledge_bus_folders: KnowledgeBusFolders,
        kind: Annotated[
            str, Field(description="The document type id, such as `design-doc`.")
        ],
        universe: Universe = None,
        format: Annotated[
            Literal["json", "markdown"] | None,
            Field(description="Defaults to `markdown`."),
        ] = None,
    ) -> CallToolResult:
        arguments = respond.sent(
            folders=folders,
            knowledge_bus_folders=knowledge_bus_folders,
            location=location,
            kind=kind,
            universe=universe,
            format=format,
        )
        argv = [
            "--card",
            kind,
            *(["--universe", universe] if universe else []),
            "--format",
            format or "markdown",
        ]
        return scoped("kbp_card", location, arguments, argv)
