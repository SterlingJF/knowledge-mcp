"""Test insertion and removal of server entries across host configuration formats."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from knowledge_mcp.configedit import (
    ConfigError,
    empty_chain,
    json_entry,
    json_insert,
    json_remove,
    toml_entry,
    toml_insert,
    toml_remove,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"

ENTRY = {"command": "/opt/homebrew/bin/kb", "args": ["mcp"]}
PATH = ("mcpServers",)

JSON_FILES = [
    "",
    "{}",
    "{ }\n",
    (FIXTURE_DIR / "two-space-indented-root-object.json").read_bytes().decode("utf-8"),
    (FIXTURE_DIR / "mcp-server-with-unrelated-root-setting.json")
    .read_bytes()
    .decode("utf-8"),
    '{"mcpServers":{}}',
    '{"a":1}',
    (FIXTURE_DIR / "commented-mcp-server-with-trailing-commas.jsonc")
    .read_bytes()
    .decode("utf-8"),
    '{\n\t"mcpServers": {\n\t\t"x": 1\n\t}\n}\n',
]


@pytest.mark.parametrize("text", JSON_FILES)
def test_json_insert_remove_restores_original_text(text):
    new, piece = json_insert(text, PATH, "knowledge-mcp", ENTRY)

    assert json_entry(new, PATH, "knowledge-mcp") == ENTRY
    assert json_remove(new, PATH, "knowledge-mcp", piece) == text


@pytest.mark.parametrize("text", JSON_FILES)
def test_json_remove_without_saved_piece_removes_entry(text):
    new, _piece = json_insert(text, PATH, "knowledge-mcp", ENTRY)

    left = json_remove(new, PATH, "knowledge-mcp", None)

    assert json_entry(left, PATH, "knowledge-mcp") is None
    assert empty_chain(left, PATH) == empty_chain(text, PATH)


def test_json_insert_rejects_existing_entries_and_invalid_config():
    with pytest.raises(ConfigError):
        json_insert(
            '{"mcpServers": {"knowledge-mcp": {}}}', PATH, "knowledge-mcp", ENTRY
        )
    with pytest.raises(ConfigError, match="line 1"):
        json_insert('{"mcpServers": ', PATH, "knowledge-mcp", ENTRY)
    with pytest.raises(ConfigError, match="not an object"):
        json_insert('{"mcpServers": []}', PATH, "knowledge-mcp", ENTRY)


TOML_FILES = [
    "",
    'model = "o3"\n',
    "a = 1",
    (FIXTURE_DIR / "existing-mcp-server-and-enabled-plugin.toml")
    .read_bytes()
    .decode("utf-8"),
]


@pytest.mark.parametrize("text", TOML_FILES)
def test_toml_insert_remove_restores_original_text(text):
    new, piece = toml_insert(text, "mcp_servers", "knowledge-mcp", ENTRY)

    assert toml_entry(new, "mcp_servers", "knowledge-mcp") == ENTRY
    assert toml_remove(new, "mcp_servers", "knowledge-mcp", piece) == text


def test_toml_remove_without_saved_piece_removes_subtables():
    new, _piece = toml_insert(TOML_FILES[3], "mcp_servers", "knowledge-mcp", ENTRY)
    new += (
        (FIXTURE_DIR / "knowledge-mcp-env-with-following-table.toml")
        .read_bytes()
        .decode("utf-8")
    )

    left = toml_remove(new, "mcp_servers", "knowledge-mcp", None)

    assert toml_entry(left, "mcp_servers", "knowledge-mcp") is None
    assert "[after]\nkept = true\n" in left
    assert '[plugins."k@k"]' in left


def test_toml_insert_rejects_inline_server_tables():
    text = 'mcp_servers = { x = { command = "y" } }\n'
    assert tomllib.loads(text) == {"mcp_servers": {"x": {"command": "y"}}}

    attempted = (
        text
        + "\n[mcp_servers.knowledge-mcp]\n"
        + f"command = {json.dumps(ENTRY['command'])}\n"
        + f"args = {json.dumps(ENTRY['args'])}\n"
    )
    with pytest.raises(tomllib.TOMLDecodeError):
        tomllib.loads(attempted)

    with pytest.raises(ConfigError) as refused:
        toml_insert(text, "mcp_servers", "knowledge-mcp", ENTRY)

    assert "TOML" in str(refused.value)
    assert isinstance(
        refused.value.__cause__ or refused.value.__context__, tomllib.TOMLDecodeError
    )
