"""MCP server over stdio, started by `kb mcp` or `python -m knowledge_mcp`."""

from __future__ import annotations

import io
import logging
import os
import stat
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

import anyio
from mcp.server import MCPServer
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server as ProtocolServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import (
    ResourceError,
    ToolError,
    UnexpectedResourceError,
    UnexpectedToolError,
)
from mcp.server.mcpserver.resolve import resolve_arguments
from mcp.server.mcpserver.tools.base import Tool as RegisteredTool
from mcp.server.mcpserver.tools.tool_manager import ToolManager
from mcp.server.stdio import stdio_server
from mcp.server.subscriptions import InMemorySubscriptionBus, ListenHandler
from mcp.shared.exceptions import MCPError
from mcp_types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    Icon,
    InputRequiredResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PaginatedRequestParams,
    ReadResourceRequestParams,
    Tool,
    ToolAnnotations,
)
from mcp_types.jsonrpc import INVALID_PARAMS
from pydantic import ValidationError

from knowledge_mcp import problems, schemas, version
from knowledge_mcp.kbp import KbpMissing
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
    proposal,
    respond,
)

INSTRUCTIONS = """\
Use the kb-write-document skill before you propose changes to, write or edit a document. Use the kb-track-document-types skill at the start of a session and after you create, move or delete a file. Use the kb-import-document skill to import a document written elsewhere. knowledge-mcp opens no knowledge-base file. You read the files and pass their content in the tool arguments. While you use knowledge-mcp, commit nothing, push nothing, open no issue or pull request, and post no comment.
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
    """Rejects unknown arguments and adds an output schema to every registered tool in the tool list.

    Raises MCPError for an unknown tool name and re-raises any MCPError from the SDK.
    Returns a problem object for other failures and attempts to log the error text.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Registration, schemas and invocation share the SDK's native metadata.
        self.tools = ToolManager()
        self.subscriptions = InMemorySubscriptionBus()

    def add_tool(  # noqa: PLR0913, PLR0917 - native SDK registration signature.
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        icons: list[Icon] | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
    ) -> None:
        self.tools.add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            icons=icons,
            meta=meta,
            structured_output=structured_output,
        )

    def remove_tool(self, name: str) -> None:
        self.tools.remove_tool(name)

    @asynccontextmanager
    async def lifespan(self, _server: ProtocolServer[Any]) -> AsyncIterator[Any]:
        if self.settings.lifespan is None:
            yield {}
        else:
            async with self.settings.lifespan(self) as state:
                yield state

    async def run_stdio_async(self) -> None:
        server = ProtocolServer(
            name=self.name,
            title=self.title,
            version=self.version,
            instructions=self.instructions,
            description=self.description,
            website_url=self.website_url,
            icons=self.icons,
            lifespan=self.lifespan,
            on_list_tools=self.list_handler,
            on_call_tool=self.call_handler,
            on_list_resources=self.resources_handler,
            on_list_resource_templates=self.templates_handler,
            on_read_resource=self.read_handler,
            on_list_prompts=self.prompts_handler,
            on_get_prompt=self.prompt_handler,
            on_subscriptions_listen=ListenHandler(self.subscriptions),
        )
        stdin = Stdin() if sys.platform != "win32" else None
        async with stdio_server(stdin=stdin) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    async def list_handler(
        self,
        _ctx: ServerRequestContext[Any],
        _params: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=await self.list_tools())

    async def call_handler(
        self,
        ctx: ServerRequestContext[Any],
        params: CallToolRequestParams,
    ) -> CallToolResult | InputRequiredResult:
        context = Context(
            request_context=ctx,
            mcp_server=self,
            input_params=params,
            subscriptions=self.subscriptions,
        )
        return cast(
            CallToolResult | InputRequiredResult,
            await self.call_tool(params.name, params.arguments or {}, context),
        )

    async def resources_handler(
        self,
        _ctx: ServerRequestContext[Any],
        _params: PaginatedRequestParams | None,
    ) -> ListResourcesResult:
        return ListResourcesResult(resources=await self.list_resources())

    async def templates_handler(
        self,
        _ctx: ServerRequestContext[Any],
        _params: PaginatedRequestParams | None,
    ) -> ListResourceTemplatesResult:
        return ListResourceTemplatesResult(
            resource_templates=await self.list_resource_templates()
        )

    async def read_handler(
        self,
        _ctx: ServerRequestContext[Any],
        params: ReadResourceRequestParams,
    ) -> Any:
        # This application registers no resources, matching the native empty registry.
        raise MCPError(
            code=INVALID_PARAMS,
            message=f"Unknown resource: {params.uri}",
            data={"uri": str(params.uri)},
        )

    async def prompts_handler(
        self,
        _ctx: ServerRequestContext[Any],
        _params: PaginatedRequestParams | None,
    ) -> ListPromptsResult:
        return ListPromptsResult(prompts=await self.list_prompts())

    async def prompt_handler(
        self,
        _ctx: ServerRequestContext[Any],
        params: GetPromptRequestParams,
    ) -> GetPromptResult | InputRequiredResult:
        return await self.get_prompt(params.name, params.arguments)

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name=info.name,
                title=info.title,
                description=info.description,
                input_schema={**info.parameters, "additionalProperties": False},
                output_schema=(
                    schemas.listed(schemas.RESULTS[info.name])
                    if info.name in schemas.RESULTS
                    else info.output_schema
                ),
                annotations=info.annotations,
                icons=info.icons,
                meta=info.meta,
            )
            for info in self.tools.list_tools()
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: Any = None,
    ) -> Any:
        tool = self.tools.get_tool(name)
        if tool is None:
            raise MCPError(code=INVALID_PARAMS, message=f"Unknown tool: {name}")
        location = arguments.get("location")
        location = location if isinstance(location, str) else ""
        names = tuple(tool.parameters.get("properties", {}))
        unknown = [key for key in arguments if key not in names]
        if unknown:
            failure = problems.unknown_arguments(name, unknown, names)
            return respond.error(name, location, arguments, failure)
        try:
            return await self.invoke(tool, arguments, context)
        except MCPError:
            raise
        except Exception as error:
            if isinstance(error, (UnexpectedToolError, UnexpectedResourceError)):
                # Transport calls carry the SDK context; local CLI calls do not.
                if context is not None:
                    logging.getLogger(__name__).exception(
                        "Tool %r raised an unexpected exception", name
                    )
                # Internal validation failures are not argument-model failures.
                # Preserve their detail without the canonical argument-title heuristic.
                if isinstance(error.__cause__, ValidationError):
                    error = RuntimeError(str(error.__cause__))
            return respond.error(
                name, location, arguments, problems.from_exception(error, name)
            )

    async def invoke(
        self,
        tool: RegisteredTool,
        arguments: dict[str, Any],
        context: Any,
    ) -> Any:
        try:
            # SDK 2.2 pre_parse_json corrupts nullable strings. Use the Pydantic
            # model generated at registration without that optional preprocessing.
            validated = tool.fn_metadata.arg_model.model_validate(
                arguments
            ).model_dump_one_level()
        except MCPError:
            raise
        except ValidationError as error:
            message = f"Invalid arguments for {tool.name}"
            raise ToolError(message) from error
        except Exception as error:
            message = f"Error executing tool {tool.name}"
            raise UnexpectedToolError(message) from error
        try:
            context = context or Context(
                mcp_server=self, subscriptions=self.subscriptions
            )
            direct = {tool.context_kwarg: context} if tool.context_kwarg else {}
            if tool.resolved_params:
                resolved = await resolve_arguments(
                    tool.resolved_params, tool.resolver_plans, validated, context
                )
                if isinstance(resolved, InputRequiredResult):
                    return tool.fn_metadata.convert_result(resolved)
                direct.update(resolved)
            result = await tool.fn_metadata.call_fn(
                tool.fn, tool.is_async, validated, direct
            )
            return tool.fn_metadata.convert_result(result)
        except MCPError, problems.Error, KbpMissing, ToolError, ResourceError:
            raise
        except Exception as error:
            message = f"Error executing tool {tool.name}"
            raise UnexpectedToolError(message) from error


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
    proposal.register(mcp, workspace)
    # App registration must stay in sync with the canonical contract registry.
    missing = {tool.name for tool in mcp.tools.list_tools()} - schemas.RESULTS.keys()
    if missing:
        message = f"App tools missing canonical result schemas: {sorted(missing)}"
        raise ValueError(message)
    return mcp


def main() -> None:
    anyio.run(build_server().run_stdio_async)
