from __future__ import annotations

import re
from pathlib import Path

import yaml

from tests.harness import server_parameters, session

TOOLS = {
    "kb_prepare_import",
    "kb_get_document_type",
    "kb_list_audiences",
    "kb_record_edit",
    "kb_list_edits",
    "kb_prepare_document_types",
    "kb_prepare_conventions",
    "kb_prepare_document_move",
    "kbp_validate",
    "kbp_self_check",
    "kbp_version",
    "kbp_mint",
    "kbp_inspect",
    "kbp_explore",
    "kbp_kinds",
    "kbp_card",
}

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


def test_authorization_meanings_reach_the_listed_input_schemas(tmp_path):
    root = Path(__file__).resolve().parents[2]
    schema = yaml.safe_load(
        (root / "contracts/extensions/mcp/v1/document-types.schema.yaml").read_text()
    )
    source = schema["$defs"]["allowed_by"]["properties"]
    for tool in listed(tmp_path):
        if tool.name in {
            "kb_record_edit",
            "kb_prepare_document_types",
            "kb_prepare_document_move",
            "kb_prepare_conventions",
        }:
            fields = tool.input_schema["$defs"]["AllowedBy"]["properties"]
            for name in ("basis", "text", "location"):
                assert fields[name].get("description") == source[name]["description"], (
                    f"{tool.name}: {name} must preserve the shared authorization meaning"
                )


def test_tool_metadata_matches_local_operation_policy(
    tmp_path,
):
    for tool in listed(tmp_path):
        words = f"{tool.name.replace('_', ' ')} {tool.title or ''}"
        assert not OUTWARD.search(words), (
            f"{tool.name}: name or title describes an external action"
        )
        assert tool.annotations is not None, f"{tool.name}: annotations are missing"
        assert tool.annotations.open_world_hint is False, (
            f"{tool.name}: openWorldHint must be false"
        )


def test_server_instructions_name_the_three_skills_and_the_no_commit_rule(tmp_path):
    async def steps(client):
        return client.instructions

    instructions = session(server_parameters(tmp_path), steps)
    assert all(
        name in instructions
        for name in (
            "kb-write-document",
            "kb-track-document-types",
            "kb-import-document",
        )
    )
    assert "commit nothing" in instructions
    assert len(instructions.split()) <= 80


def test_tool_descriptions_stay_within_80_words(tmp_path):
    verbs = {
        "Get",
        "List",
        "Prepare",
        "Record",
        "Validate",
        "Check",
        "Mint",
        "Inspect",
        "Write",
        "Read",
    }
    for tool in listed(tmp_path):
        description = tool.description or ""
        assert description.split()[0] in verbs, tool.name
        assert len(description.split()) <= 80, tool.name
        assert "log.jsonl" in description, tool.name
