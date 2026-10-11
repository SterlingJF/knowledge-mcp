"""Expected MCP tool names and annotations for local operation."""

from __future__ import annotations

import re

from tests.hosts import server_parameters, session

TOOLS = {
    "kb_mark",
    "kb_fit",
    "kb_audience",
    "kb_record_edit",
    "kb_edits",
    "kb_fit_record",
    "kbp_check",
    "kbp_self_check",
    "kbp_version",
    "kbp_mint",
    "kbp_inspect",
    "kbp_explore",
    "kbp_kinds",
    "kbp_card",
}

# Action words excluded from registered tool names and titles.
OUTWARD = re.compile(
    r"\b(commit|commits|push|pushes|issue|issues|pull|pr|merge|comment|comments|post|posts|"
    r"publish|send|reply)\b",
    re.IGNORECASE,
)


def listed(tmp_path):
    async def steps(client):
        return (await client.list_tools()).tools

    return session(server_parameters(tmp_path), steps)


def test_server_registers_exact_expected_tool_names(tmp_path):
    assert {tool.name for tool in listed(tmp_path)} == TOOLS


def test_tool_metadata_matches_local_operation_policy(
    tmp_path,
):
    for tool in listed(tmp_path):
        words = f"{tool.name.replace('_', ' ')} {tool.title or ''}"
        assert not OUTWARD.search(words), tool.name
        # Each tool declares open_world_hint=False.
        assert tool.annotations is not None, tool.name
        assert tool.annotations.open_world_hint is False, tool.name
