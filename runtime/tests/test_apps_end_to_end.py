from __future__ import annotations

import anyio
import pytest
from mcp.client import Client
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPError

from knowledge_mcp import apps
from tests.harness import server_parameters, session
from tests.test_proposal_end_to_end import DEMO, TABLE

URI = "ui://knowledge-mcp/app.html"
MIME = "text/html;profile=mcp-app"


def test_server_lists_the_app_resource_with_its_ui_meta(tmp_path):
    async def steps(client):
        return (await client.list_resources()).resources

    (resource,) = session(server_parameters(tmp_path), steps)
    assert str(resource.uri) == URI
    assert resource.mime_type == MIME
    assert resource.meta == {
        "ui": {
            "prefersBorder": True,
            "csp": {"resourceDomains": ["https://assets.claude.ai"]},
        }
    }


def test_server_reads_the_packaged_app_html(tmp_path):
    async def steps(client):
        return (await client.read_resource(URI)).contents

    (content,) = session(server_parameters(tmp_path), steps)
    assert content.mime_type == MIME
    assert content.text == apps.HTML.read_text(encoding="utf-8")
    assert content.text.lstrip().lower().startswith("<!doctype html>")


def test_only_the_card_tools_point_at_the_app(tmp_path):
    async def steps(client):
        return (await client.list_tools()).tools

    bound = {
        tool.name: (tool.meta or {}).get("ui")
        for tool in session(server_parameters(tmp_path), steps)
        if (tool.meta or {}).get("ui")
    }
    assert bound == {
        "kb_prepare_proposal": {"resourceUri": URI},
        "kb_record_edit": {"resourceUri": URI},
        "kb_prepare_document_moves": {"resourceUri": URI},
    }


def test_proposal_result_keeps_the_text_card_first(tmp_path):
    async def steps(client):
        return await client.call_tool("kb_prepare_proposal", DEMO)

    result = session(server_parameters(tmp_path), steps)
    assert not result.is_error, result.content
    assert result.content[0].text == TABLE
    assert result.structured_content["card"] == TABLE


def test_unknown_resource_is_still_refused(tmp_path):
    async def steps(client):
        with pytest.raises(MCPError, match="Unknown resource"):
            await client.read_resource("ui://knowledge-mcp/missing.html")

    session(server_parameters(tmp_path), steps)


def test_server_advertises_the_apps_extension_where_the_protocol_carries_it(
    tmp_path,
):
    # Extensions exist on the 2026-07-28 wire; older handshakes drop the field.
    async def main():
        async with Client(stdio_client(server_parameters(tmp_path))) as client:
            return client.server_capabilities.extensions

    assert anyio.run(main) == {"io.modelcontextprotocol/ui": {}}
