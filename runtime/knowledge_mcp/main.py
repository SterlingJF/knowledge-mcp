"""MCP server over stdio, started by `kb mcp` or `python -m knowledge_mcp`."""

from __future__ import annotations

import io
import os
import stat
import sys
from typing import Any

import anyio
from mcp.server import MCPServer
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import MCPError
from mcp_types import Tool
from mcp_types.jsonrpc import INVALID_PARAMS

from knowledge_mcp import problems, schemas, version
from knowledge_mcp.scope import Workspace
from knowledge_mcp.tools import (
    audience,
    convention_templates,
    conventions,
    document_move,
    document_moves,
    document_type,
    document_types,
    edits,
    importing,
    kbp,
    respond,
)

INSTRUCTIONS = """\
Use the kb-write-document skill before you write or edit a document. Use the kb-track-document-types skill at the start of a session and after you create, move or delete a file. Use the kb-import-document skill to import a document written elsewhere. knowledge-mcp opens no knowledge-base file. You read the files and pass their content in the tool arguments. While you use knowledge-mcp, commit nothing, push nothing, open no issue or pull request, and post no comment.
"""


class Stdin(anyio.AsyncFile[str]):
    """POSIX stdin reader that stays cancellable while stdin is idle."""

    def __init__(self) -> None:
        super().__init__(sys.stdin)
        self._pending = b""
        self._regular = stat.S_ISREG(os.fstat(self.wrapped.fileno()).st_mode)

    async def readline(self) -> str:
        while b"\n" not in self._pending:
            # Regular files are always readable, and Linux epoll refuses to watch them.
            if self._regular:
                await anyio.lowlevel.checkpoint()
            else:
                await anyio.wait_readable(self.wrapped.fileno())
            block = os.read(self.wrapped.fileno(), io.DEFAULT_BUFFER_SIZE)
            if not block:
                line, self._pending = self._pending, b""
                return line.decode("utf-8", errors="replace")
            self._pending += block
        line, self._pending = self._pending.split(b"\n", 1)
        return (line + b"\n").decode("utf-8", errors="replace")


class Server(MCPServer):
    """Rejects unknown arguments and adds an output schema to each `kb_*` tool in the tool list.

    Raises MCPError for an unknown tool name and re-raises any MCPError from the SDK.
    Returns a problem object for other failures and attempts to log the error text.
    """

    _arguments: dict[str, tuple[str, ...]] | None = None

    async def run_stdio_async(self) -> None:
        # The SDK reads stdin in a thread shielded from cancellation, so an idle server stops
        # only after the next line arrives. The Stdin class reads without a thread on POSIX.
        if sys.platform == "win32":
            await super().run_stdio_async()
            return
        async with stdio_server(stdin=Stdin()) as (read_stream, write_stream):
            await self._lowlevel_server.run(
                read_stream,
                write_stream,
                self._lowlevel_server.create_initialization_options(),
            )

    async def list_tools(self) -> list[Tool]:
        listed = []
        for tool in await super().list_tools():
            update: dict[str, Any] = {
                "input_schema": {**tool.input_schema, "additionalProperties": False}
            }
            if tool.name in schemas.RESULTS:
                update["output_schema"] = schemas.listed(schemas.RESULTS[tool.name])
            listed.append(tool.model_copy(update=update))
        return listed

    async def _argument_names(self) -> dict[str, tuple[str, ...]]:
        if self._arguments is None:
            self._arguments = {
                tool.name: tuple(tool.input_schema.get("properties", {}))
                for tool in await super().list_tools()
            }
        return self._arguments

    async def call_tool(
        self, name: str, arguments: dict[str, Any], context: Any = None
    ) -> Any:
        names = await self._argument_names()
        if name not in names:
            raise MCPError(code=INVALID_PARAMS, message=f"Unknown tool: {name}")
        location = arguments.get("location")
        location = location if isinstance(location, str) else ""
        unknown = [key for key in arguments if key not in names[name]]
        if unknown:
            failure = problems.unknown_arguments(name, unknown, names[name])
            return respond.error(name, location, arguments, failure)
        try:
            return await super().call_tool(name, arguments, context)
        except MCPError:
            raise
        # Other exceptions become problem objects so agents can read the error code.
        except Exception as error:  # noqa: BLE001
            failure = problems.from_exception(error, name)
            return respond.error(name, location, arguments, failure)


def build_server(workspace: Workspace | None = None) -> MCPServer:
    mcp = Server(
        name="knowledge-mcp",
        title="knowledge-mcp",
        version=version(),
        instructions=INSTRUCTIONS,
        log_level="WARNING",
    )
    workspace = workspace or Workspace()
    convention_templates.register(mcp)
    conventions.register(mcp, workspace)
    document_move.register(mcp, workspace)
    document_moves.register(mcp, workspace)
    document_type.register(mcp, workspace)
    audience.register(mcp, workspace)
    edits.register(mcp, workspace)
    document_types.register(mcp, workspace)
    importing.register(mcp, workspace)
    kbp.register(mcp, workspace)
    return mcp


def main() -> None:
    build_server().run("stdio")
