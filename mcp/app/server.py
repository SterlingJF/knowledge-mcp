# File: mcp/app/server.py
"""Backend-enforced permissions (server/app/store/service.py)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server import MCPServer

from app.front_door import FrontDoor
from app.settings import AGENT_PARTY, MCP_REVISION
from app.tools import artifacts, files, universes, vaults

if TYPE_CHECKING:
    from app.settings import Settings

INSTRUCTIONS = f"""\
knowledge-mcp holds a person's thinking as typed records rather than prose.

You are acting as {AGENT_PARTY}. Everything you write is recorded in your name, and every record
you write must say so: set `asserted_by` to "{AGENT_PARTY}" on each one. You cannot write in the
person's name, and you cannot commit.

Read a universe before writing anything. It says which artifact types exist, which elements each
is made of, and which statuses an instance record may carry. Elements and artifact types travel as
short opaque codes; resolve them against the universe for your own use, and never show a code to a
person — use the label.

You draft; the person commits. Leave an artifact as a draft, tell them what it says, and let them
commit it themselves. `km_commit_artifact` exists so you can ask and relay the answer.\
"""


def build_server(settings: Settings) -> Any:
    mcp = MCPServer(
        name=settings.APP_NAME,
        title='Knowledge MCP',
        version='0.1.0',
        instructions=INSTRUCTIONS,
        log_level=settings.LOG_LEVEL,  # type: ignore[arg-type]
    )

    artifacts.register(mcp)
    files.register(mcp)
    universes.register(mcp)
    vaults.register(mcp)

    return mcp


def build_app(settings: Settings) -> Any:
    """HTTP application behind protocol-revision gate (app.front_door)."""
    mcp = build_server(settings)
    app = mcp.streamable_http_app(
        streamable_http_path='/mcp',
        stateless_http=True,
        host=settings.HOST,
    )
    return FrontDoor(app)


def describe(settings: Settings) -> str:
    return (
        f'{settings.APP_NAME} revision={MCP_REVISION} '
        f'listening=http://{settings.HOST}:{settings.PORT}/mcp '
        f'backend={settings.API_ORIGIN} acting-as={AGENT_PARTY}'
    )
