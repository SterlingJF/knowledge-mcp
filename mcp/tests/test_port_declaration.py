# File: mcp/tests/test_port_declaration.py
"""Plugin manifest has no port placeholder. Manifest port must match `DEFAULT_PORT`."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from app.settings import DEFAULT_PORT

PLUGIN_MANIFEST = (
    Path(__file__).resolve().parents[1] / 'plugin' / 'knowledge-mcp' / 'mcp.json'
)

SERVER_KEY = 'knowledge-mcp'


def _manifest() -> dict:
    return json.loads(PLUGIN_MANIFEST.read_text(encoding='utf-8'))


def test_the_plugin_manifest_names_the_port_this_server_listens_on():
    url = _manifest()['mcpServers'][SERVER_KEY]['url']
    declared = urlparse(url).port

    assert declared == DEFAULT_PORT, (
        f'{PLUGIN_MANIFEST.name} points at port {declared} and this server listens on '
        f'{DEFAULT_PORT}. An agent host would connect to nothing and report only that the '
        f'server is unavailable. Change one to match the other.'
    )


def test_the_plugin_manifest_uses_the_transport_this_server_serves():
    server = _manifest()['mcpServers'][SERVER_KEY]

    assert server['type'] == 'streamable-http'
    assert urlparse(server['url']).path == '/mcp'


def test_the_server_key_is_the_one_tool_names_are_built_from():
    assert set(_manifest()['mcpServers']) == {SERVER_KEY}
