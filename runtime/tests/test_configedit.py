from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
from json5.loader import ModelLoader, loads
from json5.model import Infinity, UnaryOp

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


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
@pytest.mark.parametrize("ending", ["", "\n"])
def test_jsonc_preserves_comments_unicode_and_newlines(newline, ending):
    text = (
        newline.join(
            [
                "\ufeff{/* before */",
                '  "mcpServers": { /* keep inside */ "other": {"url": "https://é.test/😀"}, },',
                '  "array": [1, false, null,], /* after */',
                "}",
            ]
        )
        + ending
    )
    new, piece = json_insert(text, PATH, "knowledge-mcp", ENTRY)
    assert json_entry(new, PATH, "knowledge-mcp") == ENTRY
    assert new.replace(piece, "", 1).encode() == text.encode()
    assert json_remove(new, PATH, "knowledge-mcp", piece).encode() == text.encode()
    removed = json_remove(new, PATH, "knowledge-mcp", None)
    assert "/* keep inside */" in removed
    assert '"other": {"url": "https://é.test/😀"}' in removed
    assert '"array": [1, false, null,], /* after */' in removed


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1 "b": 2}',
        '{"a": [1 2]}',
        '{"a": /* unfinished',
        '{"a": "unterminated}',
        '{"a": 1} trailing',
    ],
)
def test_jsonc_rejects_malformed_settings(text):
    with pytest.raises((ConfigError, json.JSONDecodeError)):
        json_insert(text, PATH, "knowledge-mcp", ENTRY)


@pytest.mark.parametrize(
    "text",
    [
        "{true: 1}",
        '{"x": NaN}',
        '{"x": Infinity}',
        "{'x': 1}",
        '{"x": +1}',
        '{"x": 0x10}',
    ],
)
def test_jsonc_rejects_json5_only_literals(text):
    with pytest.raises((ConfigError, json.JSONDecodeError)):
        json_insert(text, PATH, "knowledge-mcp", ENTRY)


@pytest.mark.parametrize(
    "text",
    [
        "{ /* keep empty object comment */ }",
        '{"other": 1, /* before */ "knowledge-mcp": {}, /* after */}',
        '{"knowledge-mcp": {}, /* next */ "other": 1}',
        '{"other": 1, /* last */ "knowledge-mcp": {}}',
    ],
)
def test_jsonc_removal_without_receipt_keeps_unrelated_comments(text):
    if json_entry(text, (), "knowledge-mcp") is None:
        text, _ = json_insert(text, (), "knowledge-mcp", ENTRY)
    removed = json_remove(text, (), "knowledge-mcp", None)
    assert re.findall(r"/\*.*?\*/", removed) == re.findall(r"/\*.*?\*/", text)
    assert json_entry(removed, (), "knowledge-mcp") is None
    assert json_entry(removed, (), "other") == json_entry(text, (), "other")


@pytest.mark.parametrize(
    "constant", ["Infinity", "-Infinity", "+Infinity", "NaN", "-NaN", "+NaN"]
)
def test_jsonc_signed_non_json_constants_are_rejected(constant):
    text = '{"x": ' + constant + "}"
    if constant == "-Infinity":
        model = loads(text, loader=ModelLoader()).value.key_value_pairs[0][1]
        assert isinstance(model, UnaryOp)
        assert isinstance(model.value, Infinity)
    with pytest.raises((ConfigError, json.JSONDecodeError)):
        json_insert(text, PATH, "knowledge-mcp", ENTRY)
    if constant == "-Infinity":
        with pytest.raises(ConfigError, match="line 1: JSON number expected"):
            json_insert(text, PATH, "knowledge-mcp", ENTRY)
