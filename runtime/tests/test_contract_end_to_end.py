from __future__ import annotations

import hashlib
import importlib
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import pytest
from jsonschema import Draft202012Validator
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.shared.exceptions import MCPError

from knowledge_mcp import kbp
from tests.harness import BUNDLED, CODEBASE, PRODUCT, header, texts
from tests.kb_cli import kb_mcp

MODES = ["legacy", "auto"]

BASE = "https://github.com/SterlingJF/knowledge-mcp/problems/"
CODES = {
    "conventions-invalid",
    "conventions-unsupported",
    "filing-values-invalid",
    "argument-invalid",
    "scope-invalid",
    "digest-unknown",
    "record-invalid",
    "move-invalid",
    "move-input-incomplete",
    "document-type-unknown",
    "kbp-failed",
    "kbp-version-skew",
    "internal-error",
}
PROBLEM_FIELDS = {"type", "title", "detail", "errors"}

TAGS = {
    "kb_prepare_conventions": "knowledge-mcp/conventions-update/1",
    "kb_get_document_type": "knowledge-mcp/document-type/1",
    "kb_list_audiences": "knowledge-mcp/audiences/1",
    "kb_prepare_import": "knowledge-mcp/import/1",
    "kb_prepare_document_types": "knowledge-mcp/document-types-update/1",
    "kb_record_edit": "knowledge-mcp/edit/1",
    "kb_list_edits": "knowledge-mcp/edits/1",
    "kb_prepare_document_move": "knowledge-mcp/document-move/1",
}
ISSUES = "https://github.com/SterlingJF/knowledge-mcp/issues"

NOTES = "~/notes"
RFC = "docs/rfcs/0042-cache.md"
DESIGN = "DESIGN.md"
PLUGIN = ".knowledge-bus/plugins/knowledge-mcp"
ALLOWED = {
    "basis": "instruction",
    "text": "Keep the document types in .knowledge-bus/plugins/knowledge-mcp/ up to date.",
    "location": "AGENTS.md",
}


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def at(path: str) -> str:
    return f"{NOTES}/{path}"


def bundled_headers() -> list[dict[str, str]]:
    files = []
    for universe_id in (CODEBASE, PRODUCT):
        for source in sorted((BUNDLED / universe_id).glob("*.kbp.yaml")):
            name = source.name.replace("universe.kbp.yaml", "kbp.yaml")
            files.append(
                {"name": f"{universe_id}.{name}", **header(source.read_text())}
            )
    return files


def root_folder() -> dict[str, Any]:
    return {"folder": "", "files": bundled_headers()}


def document(path: str) -> dict[str, Any]:
    return {
        "location": at(path),
        "folders": list(Path(path).parts[:-1]),
        "knowledge_bus_folders": [root_folder()],
    }


def type_call(path: str = RFC, **extra: Any) -> dict[str, Any]:
    return {**document(path), "name": Path(path).name, **extra}


def audiences_call(document_type: str, **extra: Any) -> dict[str, Any]:
    return {**document(RFC), "document_type": document_type, **extra}


def import_call(**extra: Any) -> dict[str, Any]:
    return {
        "location": "pasted in chat",
        "text": "# Cache rollout\n\nWe drop the evening build.\n",
        "folders": [],
        "knowledge_bus_folders": [root_folder()],
        **extra,
    }


def update_call(**extra: Any) -> dict[str, Any]:
    return {
        "location": NOTES,
        "record": "",
        "knowledge_bus_folders": [root_folder()],
        "allowed_by": ALLOWED,
        **extra,
    }


def edit_call(**extra: Any) -> dict[str, Any]:
    return {
        "location": at(DESIGN),
        "allowed_by": {"basis": "request", "text": "Add an Overview section."},
        "before": "# Design\n",
        "after": "# Design\n\n## Overview\n",
        **extra,
    }


def server(tmp_path: Path, **extra_env: str) -> StdioServerParameters:
    parameters = kb_mcp(tmp_path)
    return parameters.model_copy(
        update={"env": {**(parameters.env or {}), **extra_env}}
    )


def run(parameters: StdioServerParameters, steps: Any, mode: str = "legacy") -> Any:
    async def main() -> Any:
        async with Client(stdio_client(parameters), mode=mode) as client:
            return await steps(client)

    return anyio.run(main)


def calls(
    tmp_path: Path, *sent: tuple[str, dict[str, Any]], mode: str = "legacy", **env: str
) -> list[Any]:
    async def steps(client: Client) -> list[Any]:
        return [await client.call_tool(name, arguments) for name, arguments in sent]

    return run(server(tmp_path, **env), steps, mode)


def tools(tmp_path: Path, mode: str = "legacy") -> dict[str, Any]:
    async def steps(client: Client) -> dict[str, Any]:
        return {tool.name: tool for tool in (await client.list_tools()).tools}

    return run(server(tmp_path), steps, mode)


def walk(node: Any) -> Iterator[tuple[str, Any, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value, node
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def own_text(result: Any) -> list[str]:
    return [
        block.text for block in result.content if not (block.meta or {}).get("stream")
    ]


def answer_of(result: Any, tool: str) -> dict[str, Any]:
    assert not result.is_error, texts(result)
    assert result.structured_content is not None, f"{tool}: no structured content"
    [text] = texts(result)
    assert result.structured_content == json.loads(text), tool
    return result.structured_content


def problem(result: Any, code: str) -> dict[str, Any]:
    assert result.is_error, texts(result)
    found = result.structured_content
    assert found is not None, f"no problem object; the text reads {texts(result)!r}"
    assert found.get("type") == BASE + code, found
    assert set(found) <= PROBLEM_FIELDS, found
    assert isinstance(found.get("title"), str), found
    assert found.get("detail"), found
    assert own_text(result)[0] == found["detail"]
    assert not any("Traceback" in text for text in texts(result))
    return found


def pointers(found: dict[str, Any]) -> list[str]:
    return [item["pointer"] for item in found.get("errors", [])]


def resolved(schema: dict[str, Any], node: Any) -> Any:
    while isinstance(node, dict) and str(node.get("$ref", "")).startswith("#/"):
        target = schema
        for part in node["$ref"][2:].split("/"):
            target = target[part]
        node = target
    return node


@pytest.mark.parametrize("mode", MODES)
def test_every_kb_tool_lists_a_result_schema_with_an_object_root(tmp_path, mode):
    listed = tools(tmp_path, mode)

    assert {name for name in listed if name.startswith("kb_")} == set(TAGS)
    for name, tool in listed.items():
        if name.startswith("kbp_"):
            assert tool.output_schema is None, name
            continue
        schema = tool.output_schema
        assert schema is not None, f"{name} lists no outputSchema"
        assert schema.get("type") == "object", name
        assert len(schema.get("oneOf", [])) == 2, name
        assert not [key for key, _, _ in walk(schema) if key == "$schema"], name
        Draft202012Validator.check_schema(schema)
        types = {
            value
            for key, value, _ in walk(schema)
            if key == "const" and isinstance(value, str) and value.startswith(BASE)
        }
        assert types == {BASE + code for code in CODES}, name


@pytest.mark.parametrize("mode", MODES)
def test_every_input_schema_refuses_unknown_arguments(tmp_path, mode):
    for name, tool in tools(tmp_path, mode).items():
        assert tool.input_schema.get("additionalProperties") is False, name


def test_read_only_tools_set_no_idempotent_hint_and_explore_is_destructive(tmp_path):
    listed = tools(tmp_path)

    for name, tool in listed.items():
        hints = tool.annotations
        assert hints is not None, name
        if hints.read_only_hint:
            assert hints.idempotent_hint is None, name
    assert listed["kbp_explore"].annotations.read_only_hint is False
    assert listed["kbp_explore"].annotations.destructive_hint is True


def test_each_kb_tool_answers_with_structured_content_equal_to_its_text(tmp_path):
    """The text block supports clients that display text without structured content."""
    results = calls(
        tmp_path,
        ("kb_prepare_conventions", {"location": NOTES, "conventions": ""}),
        ("kb_get_document_type", type_call()),
        ("kb_list_audiences", audiences_call("design-doc")),
        ("kb_prepare_import", import_call()),
        ("kb_prepare_document_types", update_call(listing=[{"path": RFC}])),
        ("kb_record_edit", edit_call()),
        ("kb_list_edits", {"location": at(DESIGN)}),
        (
            "kb_prepare_document_move",
            {
                "location": NOTES,
                "old_path": RFC,
                "path": "docs/cache.md",
                "listing": [{"path": RFC}],
                "documents": [{"path": RFC, "text": "# Cache\n"}],
                "case_mode": "sensitive",
                "record": "",
                "knowledge_bus_folders": [root_folder()],
                "allowed_by": ALLOWED,
            },
        ),
    )

    for tool, result in zip(TAGS, results, strict=True):
        found = answer_of(result, tool)
        assert found["schema"] == TAGS[tool], tool
        misnamed = [
            parent
            for key, _, parent in walk(found)
            if key == "kind" and "form" not in parent and "lines" not in parent
        ]
        assert not misnamed, f"{tool}: `kind` names a document type in {misnamed[:1]}"


def test_the_two_folder_tools_take_one_folder_shape(tmp_path):
    listed = tools(tmp_path)
    shapes = []
    for name in (
        "kb_get_document_type",
        "kb_prepare_document_types",
        "kb_prepare_conventions",
    ):
        schema = listed[name].input_schema
        assert "universe_specs" not in schema["properties"], name
        folders = resolved(schema, schema["properties"]["knowledge_bus_folders"])
        shapes.append(resolved(schema, folders["items"]))
    assert all(shape == shapes[0] for shape in shapes)

    folders = [root_folder()]
    typed, prepared = calls(
        tmp_path,
        ("kb_get_document_type", type_call(knowledge_bus_folders=folders)),
        (
            "kb_prepare_document_types",
            update_call(knowledge_bus_folders=folders, listing=[{"path": RFC}]),
        ),
    )
    answer_of(typed, "kb_get_document_type")
    answer_of(prepared, "kb_prepare_document_types")


def test_record_edit_takes_allowed_by_and_lists_it_back(tmp_path):
    allowed_by = {
        "basis": "accepted_change",
        "text": "Overview: add the personality line.",
        "location": "docs/changes.md",
    }
    recorded, listed = calls(
        tmp_path,
        ("kb_record_edit", edit_call(allowed_by=allowed_by)),
        ("kb_list_edits", {"location": at(DESIGN)}),
    )

    receipt = answer_of(recorded, "kb_record_edit")
    [edit] = answer_of(listed, "kb_list_edits")["edits"]
    assert receipt["allowed_by"] == allowed_by
    assert edit["allowed_by"] == allowed_by
    assert edit["id"] == receipt["id"]
    assert not {"basis", "basis_text", "basis_location"} & (set(receipt) | set(edit))


def test_edits_recorded_before_the_change_still_list(tmp_path):
    location = "https://www.notion.so/team/Design-0123456789abcdef"
    old = [
        {
            "id": "0" * 31 + "1",
            "time": "2026-10-12T09:15:02.118Z",
            "location": location,
            "basis": "line",
            "basis_text": "Agents may fill in empty sections of design notes.",
            "basis_location": "AGENTS.md",
            "before": "",
            "before_digest": digest(""),
            "after": "## Overview\n",
            "after_digest": digest("## Overview\n"),
        },
        {
            "id": "0" * 31 + "2",
            "time": "2026-10-12T09:16:40.003Z",
            "location": location,
            "basis": "change_row",
            "basis_text": "Overview: add the personality line.",
            "basis_location": "docs/changes.md",
            "before": "## Overview\n",
            "before_digest": digest("## Overview\n"),
            "after": "## Overview\n\nCalm and exact.\n",
            "after_digest": digest("## Overview\n\nCalm and exact.\n"),
        },
    ]
    state = tmp_path / "state" / "knowledge-mcp"
    state.mkdir(parents=True)
    (state / "edits.jsonl").write_text("".join(json.dumps(line) + "\n" for line in old))

    [listed] = calls(tmp_path, ("kb_list_edits", {"location": location}))

    edits = answer_of(listed, "kb_list_edits")["edits"]
    assert [edit["allowed_by"] for edit in edits] == [
        {"basis": "instruction", "text": old[0]["basis_text"], "location": "AGENTS.md"},
        {
            "basis": "accepted_change",
            "text": old[1]["basis_text"],
            "location": "docs/changes.md",
        },
    ]
    for edit, line in zip(edits, old, strict=True):
        assert {
            name: edit[name] for name in ("id", "before", "after", "after_digest")
        } == {name: line[name] for name in ("id", "before", "after", "after_digest")}
        assert not {"basis", "basis_text", "basis_location"} & set(edit)


@pytest.mark.parametrize(
    ("tool", "arguments", "name"),
    [
        (
            "kb_get_document_type",
            type_call(digest="sha256:" + "1" * 64),
            "digest",
        ),
        (
            "kb_list_audiences",
            audiences_call("design-doc", universe=PRODUCT),
            "universe",
        ),
        (
            "kb_prepare_document_types",
            update_call(universe_specs=[root_folder()]),
            "universe_specs",
        ),
    ],
    ids=[
        "digest-for-record_digest",
        "universe-for-universe_spec",
        "old-universe_specs",
    ],
)
def test_an_unknown_argument_is_refused_and_names_the_argument(
    tmp_path, tool, arguments, name
):
    [result] = calls(tmp_path, (tool, arguments))

    found = problem(result, "argument-invalid")
    assert pointers(found) == [f"#/{name}"]
    assert re.search(rf"\b{name}\b", found["detail"]), found["detail"]


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("kb_record_edit", edit_call(allowed_by={"basis": "line", "text": "x"})),
        (
            "kb_prepare_document_types",
            update_call(
                record="schema: knowledge-mcp/document-types/1\n"
                "# private-marker-7f3a: text the agent sent\nfiles: {}\n",
                allowed_by={"basis": "line", "text": "x"},
            ),
        ),
    ],
    ids=["kb_record_edit", "kb_prepare_document_types"],
)
def test_a_bad_argument_value_names_the_argument_and_echoes_no_input(
    tmp_path, tool, arguments
):
    [result] = calls(tmp_path, (tool, arguments))

    found = problem(result, "argument-invalid")
    assert pointers(found) == ["#/allowed_by/basis"]
    returned = " ".join(texts(result)) + json.dumps(found)
    assert "errors.pydantic.dev" not in returned
    assert "private-marker-7f3a" not in returned
    assert "input_value" not in returned


def test_an_unknown_digest_is_digest_unknown(tmp_path):
    unknown = "sha256:" + "2" * 64
    custom = {
        "name": "custom.kbp.yaml",
        "id": "custom-notes",
        "version": "1",
        "digest": unknown,
    }
    record_digest, spec_digest = calls(
        tmp_path,
        ("kb_get_document_type", type_call(record_digest=unknown)),
        (
            "kb_get_document_type",
            type_call(knowledge_bus_folders=[{"folder": "", "files": [custom]}]),
        ),
    )

    assert pointers(problem(record_digest, "digest-unknown")) == ["#/record_digest"]
    assert pointers(problem(spec_digest, "digest-unknown")) == [
        "#/knowledge_bus_folders/0/files/0/digest"
    ]


ENTRY = f"""\
    universe_spec: {CODEBASE}
    version: '0.1'
    document_type: design-proposal
    set_by: agent
    time: '2026-10-12T09:15:02.118Z'
"""
ALLOWED_YAML = """\
    allowed_by:
      basis: request
      text: It is a design proposal.
"""


@pytest.mark.parametrize(
    "record",
    [
        "schema: knowledge-mcp/document-types/1\nfiles: {docs: [\n",
        f"schema: knowledge-mcp/document-types/1\nfiles:\n  {RFC}:\n{ENTRY}",
        (
            f"schema: knowledge-mcp/document-types/1\nfiles:\n  {RFC}:\n{ENTRY}"
            f"    no_document_type: true\n{ALLOWED_YAML}"
        ),
    ],
    ids=["no-yaml", "entry-without-allowed_by", "typed-and-untyped"],
)
def test_an_invalid_document_types_text_is_record_invalid(tmp_path, record):
    [result] = calls(
        tmp_path, ("kb_prepare_document_types", update_call(record=record))
    )

    found = problem(result, "record-invalid")
    assert pointers(found) == ["#/record"]
    if "files: {docs: [" in record:
        assert "line 3, column 1" in found["detail"]
        assert found["detail"].endswith(
            "Correct the YAML, then resend the text as `record`."
        )
    else:
        assert RFC in found["detail"], found["detail"]


def test_an_unknown_document_type_is_document_type_unknown(tmp_path):
    entry = {
        "path": RFC,
        "set_by": "agent",
        "universe_spec": CODEBASE,
        "document_type": "no-such-type",
    }
    audiences, prepared = calls(
        tmp_path,
        ("kb_list_audiences", audiences_call("no-such-type")),
        ("kb_prepare_document_types", update_call(entries=[entry])),
    )

    assert pointers(problem(audiences, "document-type-unknown")) == ["#/document_type"]
    assert pointers(problem(prepared, "document-type-unknown")) == [
        "#/entries/0/document_type"
    ]


def test_complete_folder_inventory_is_allowed_and_duplicate_folders_are_invalid(
    tmp_path,
):
    twice = [root_folder(), root_folder()]
    off_chain = [root_folder(), {"folder": "team", "files": []}]
    typed_twice, typed_off, prepared_twice = calls(
        tmp_path,
        ("kb_get_document_type", type_call(knowledge_bus_folders=twice)),
        ("kb_get_document_type", type_call(knowledge_bus_folders=off_chain)),
        ("kb_prepare_document_types", update_call(knowledge_bus_folders=twice)),
    )

    assert not typed_off.is_error
    for result in (typed_twice, prepared_twice):
        assert pointers(problem(result, "scope-invalid")) == [
            "#/knowledge_bus_folders/1/folder"
        ]


def test_a_kbp_failure_inside_a_kb_tool_is_kbp_failed_with_kbp_output(tmp_path):
    workspace_yaml = f"from_parent:\n  - {PRODUCT}\n"
    path = "team/notes/pricing.md"
    arguments = {
        "location": at(path),
        "name": "pricing.md",
        "folders": ["team", "notes"],
        "knowledge_bus_folders": [
            {"folder": "", "files": []},
            {"folder": "team", "files": [], "workspace_yaml": workspace_yaml},
        ],
    }
    [result] = calls(tmp_path, ("kb_get_document_type", arguments))

    found = problem(result, "kbp-failed")
    assert re.search(r"\bkbp\b.*\bexited with code 1\b", found["detail"]), found[
        "detail"
    ]
    [stderr] = [
        block.text
        for block in result.content
        if (block.meta or {}).get("stream") == "stderr"
    ]
    assert json.loads(stderr)["schema"] == "knowledge-bus/inspection-error/1"
    assert (result.meta or {}).get("exit_code") == 1
    assert result.content[-1].text == found["detail"]
    assert found["detail"].endswith("exited with code 1.")


def test_kbp_output_under_another_schema_is_kbp_version_skew():
    problems = importlib.import_module("knowledge_mcp.problems")
    printed = kbp.Printed('{"schema": "knowledge-bus/kinds/2"}', "", 0)

    with pytest.raises(problems.Error) as raised:
        kbp.parsed(printed, "kinds", kbp.KINDS)

    assert raised.value.code == "kbp-version-skew"


def test_an_unknown_tool_is_a_protocol_error(tmp_path):

    async def steps(client: Client) -> None:
        with pytest.raises(MCPError) as raised:
            await client.call_tool("kb_fit", type_call())
        assert raised.value.code == -32602

    run(server(tmp_path), steps)


def test_an_unexpected_failure_is_internal_error_without_a_traceback(tmp_path):
    state = tmp_path / "state-file"
    state.write_text("not a folder\n")

    [result] = calls(
        tmp_path,
        ("kb_list_edits", {"location": at(DESIGN)}),
        KNOWLEDGE_MCP_STATE_DIR=str(state),
    )

    found = problem(result, "internal-error")
    assert str(state) in found["detail"], found["detail"]
    assert ISSUES in found["detail"], found["detail"]
