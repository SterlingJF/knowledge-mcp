"""Byte-faithful nullable text through the native SDK stdio boundary."""

from __future__ import annotations

import hashlib
import json

import anyio
import pytest
import yaml
from mcp.client import Client
from mcp.client.stdio import stdio_client

from tests.harness import server_parameters, session
from tests.test_document_move_end_to_end import arguments as single_arguments
from tests.test_document_moves_end_to_end import arguments as batch_arguments
from tests.test_filing_end_to_end import PERMISSION

# Verbatim km0013 raw JSON fixtures; these bytes reproduced the SDK 2.2 defect.
CUSTOM = '{\n  "schema": "knowledge-mcp/document-types/1",\n  "files": {\n    "Inbox/Note.md": {\n      "universe_spec": "product-development",\n      "version": "1",\n      "document_type": "decision-record",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "future reader",\n        "status": "confirmed"\n      }\n    }\n  }\n}\n'
ACE = '{\n  "schema": "knowledge-mcp/document-types/1",\n  "files": {\n    "Inbox/Note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "daily-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/knowledge-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "knowledge-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/meeting-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "meeting-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/project-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "project-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/area-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "area-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/resource-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "resource-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/archived-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "archived-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/decision-record.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "decision-record",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "Review/field-note.md": {\n      "universe_spec": "personal-notes",\n      "version": "1",\n      "document_type": "field-note",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "note author",\n        "status": "confirmed"\n      }\n    },\n    "docs/rfcs/0042-cache.md": {\n      "universe_spec": "codebase-recordkeeping",\n      "version": "1",\n      "document_type": "design-proposal",\n      "set_by": "person",\n      "allowed_by": {\n        "basis": "request",\n        "text": "Fictional QA input: keep these supplied types and readers."\n      },\n      "time": "2026-10-18T00:00:00Z",\n      "audience": {\n        "value": "maintainer",\n        "status": "confirmed"\n      }\n    }\n  }\n}\n'


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def args_for(tool):
    if tool == "kb_prepare_document_move":
        return single_arguments({"Inbox/Note.md": "# Note\n"})
    if tool == "kb_prepare_document_moves":
        return batch_arguments(
            {"Inbox/Note.md": "# Note\n"},
            [("Inbox/Note.md", "Notes/Note.md")],
            allowed_by=PERMISSION,
        )
    args = {"location": "unreachable://fidelity", "knowledge_bus_folders": []}
    if tool == "kb_get_document_type":
        args.update(name="Note.md", folders=[])
    return args


TOOLS = [
    "kb_prepare_document_types",
    "kb_get_document_type",
    "kb_prepare_document_move",
    "kb_prepare_document_moves",
]


async def searched_arguments(client, tool):
    args = args_for(tool)
    args.pop("record", None)
    if tool in TOOLS[2:]:
        preview = await client.call_tool(tool, {**args, "record": CUSTOM})
        assert not preview.is_error, preview.structured_content
        assert preview.structured_content["status"] == "texts_needed"
        args.update(searched=True, search=preview.structured_content["search"])
    return args


def received(answer):
    return {item["name"]: item["digest"] for item in answer["received"]}


@pytest.mark.parametrize(
    "text,sha",
    [
        (CUSTOM, "260af191b3186640888ded8955f5895020ca7e17a5aa31efc513aaf37d66d1b3"),
        (ACE, "01611fb3d1badcf8180493b0a5490d74635bf628bc98b2cdc36945f0d99b5e80"),
    ],
)
@pytest.mark.parametrize("representation", ["json", "yaml"])
def test_exact_failed_fixture_bytes_and_digest_recall(
    tmp_path, text, sha, representation
):
    assert digest(text) == "sha256:" + sha
    assert len(text.encode("utf-8")) == (498 if text == CUSTOM else 4380)
    if representation == "yaml":
        text = yaml.safe_dump(json.loads(text), sort_keys=False, allow_unicode=True)

    async def steps(client):
        for tool in TOOLS:
            args = await searched_arguments(client, tool)
            first = await client.call_tool(tool, {**args, "record": text})
            assert not first.is_error, first.structured_content
            answer = first.structured_content
            assert received(answer)[
                ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml"
            ] == digest(text)
            if tool != "kb_get_document_type":
                based_on = answer["based_on"]
                assert (
                    based_on["record_digest"]
                    if isinstance(based_on, dict)
                    else based_on
                ) == digest(text)
            recalled = await client.call_tool(
                tool, {**args, "record_digest": digest(text)}
            )
            assert not recalled.is_error, recalled.structured_content
            for key in (
                "based_on",
                "status",
                "record",
                "recorded",
                "candidates",
                "writes",
            ):
                if key in answer:
                    assert recalled.structured_content[key] == answer[key]

    session(server_parameters(tmp_path), steps)


@pytest.mark.parametrize("tool", TOOLS)
def test_record_text_variants_remain_text_over_stdio(tmp_path, tool):
    base = args_for(tool)
    original = base.pop("record", CUSTOM)
    data = yaml.safe_load(original)
    variants = [
        original,
        json.dumps(data, ensure_ascii=False),
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        " \r\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\r\n ",
        "# café 雪 🦊\r\n" + yaml.safe_dump(data, sort_keys=False) + "\n",
    ]

    async def steps(client):
        args = await searched_arguments(client, tool)
        for text in [*variants, "", "null", "[]"]:
            result = await client.call_tool(tool, {**args, "record": text})
            answer = result.structured_content
            if text == "[]":
                assert result.is_error, answer
                assert answer["type"].endswith("/record-invalid"), answer
            else:
                assert not result.is_error, answer
                assert received(answer)[
                    ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml"
                ] == digest(text)
                if tool != "kb_get_document_type":
                    based_on = answer["based_on"]
                    assert (
                        based_on["record_digest"]
                        if isinstance(based_on, dict)
                        else based_on
                    ) == digest(text)
                recalled = await client.call_tool(
                    tool, {**args, "record_digest": digest(text)}
                )
                assert not recalled.is_error, recalled.structured_content
                for key in (
                    "based_on",
                    "status",
                    "record",
                    "recorded",
                    "candidates",
                    "writes",
                ):
                    if key in answer:
                        assert recalled.structured_content[key] == answer[key]
        omitted = await client.call_tool(tool, base)
        explicit = await client.call_tool(tool, {**base, "record": None})
        assert omitted.is_error == explicit.is_error
        assert omitted.structured_content == explicit.structured_content
        rejected = await client.call_tool(tool, {**base, "record": data})
        assert rejected.is_error
        assert rejected.structured_content["type"].endswith("/argument-invalid")
        assert any(
            e["pointer"] == "#/record" for e in rejected.structured_content["errors"]
        )

    session(server_parameters(tmp_path), steps)


@pytest.mark.parametrize(
    "tool",
    ["kb_prepare_conventions", "kb_get_document_type", "kb_prepare_document_types"],
)
def test_nullable_conventions_text_over_stdio(tmp_path, tool):
    base = args_for(tool)
    text = '{"schema":"knowledge-mcp/conventions/1","from_parent":[],"conventions":[]}'

    async def steps(client):
        for value in [
            text,
            " \r\n" + text + "\r\n",
            yaml.safe_dump(json.loads(text)),
            "",
            "null",
            "[]",
        ]:
            result = await client.call_tool(
                tool,
                {**base, "record": "", "conventions": value}
                if tool != "kb_prepare_conventions"
                else {**base, "conventions": value},
            )
            answer = result.structured_content
            if value in {"null", "[]"}:
                assert result.is_error, answer
                assert answer["type"].endswith("/conventions-invalid"), answer
            else:
                assert not result.is_error, answer
            if not result.is_error and value:
                assert received(answer)[
                    ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"
                ] == digest(value)
        args = {**base, "record": ""} if tool != "kb_prepare_conventions" else base
        omitted = await client.call_tool(tool, args)
        explicit = await client.call_tool(tool, {**args, "conventions": None})
        assert omitted.is_error == explicit.is_error
        assert omitted.structured_content == explicit.structured_content
        rejected = await client.call_tool(
            tool, {**args, "conventions": json.loads(text)}
        )
        assert rejected.is_error
        assert rejected.structured_content["type"].endswith("/argument-invalid")

    session(server_parameters(tmp_path), steps)


NATIVE_SERVER = """
from contextlib import asynccontextmanager
from pathlib import Path
import os
from pydantic import BaseModel, create_model
from mcp.server.mcpserver import Context
from knowledge_mcp.main import Server
from knowledge_mcp import problems
from knowledge_mcp.tools import respond

marker = Path(os.environ["KNOWLEDGE_MCP_STATE_DIR"]) / "lifecycle"
@asynccontextmanager
async def lifespan(server):
    marker.write_text("entered")
    try:
        yield {"value": "live"}
    finally:
        marker.write_text("exited")
server = Server(name="native-fidelity", lifespan=lifespan)
class Answer(BaseModel):
    value: str | None
    lifecycle: str
@server.tool(title="Echo raw text")
def echo(ctx: Context, value: str | None = None):
    data = {"value": value, "lifecycle": ctx.request_context.lifespan_context["value"]}
    return respond.answer("echo", "", {"value": value}, Answer, data)
@server.tool()
async def async_echo(ctx: Context, value: str | None = None):
    return echo(ctx, value)
@server.tool()
def domain():
    raise problems.Error("domain rejected", code="record-invalid")
@server.tool()
def crash():
    raise RuntimeError("private diagnostic sentinel")
@server.tool()
def internal_validation():
    create_model("InternalArguments", value=(str, ...)).model_validate({"value": {}})
server.run("stdio")
"""


def test_native_context_lifespan_error_classification_and_log_once(tmp_path):
    parameters = server_parameters(
        tmp_path, KNOWLEDGE_MCP_STATE_DIR=str(tmp_path)
    ).model_copy(update={"args": ["-c", NATIVE_SERVER]})
    diagnostics = tmp_path / "server.stderr"

    async def steps():
        with diagnostics.open("w") as errlog:
            async with Client(
                stdio_client(parameters, errlog=errlog), mode="legacy"
            ) as client:
                listed = {tool.name: tool for tool in (await client.list_tools()).tools}
                assert listed["echo"].title == "Echo raw text"
                assert set(listed["echo"].input_schema["properties"]) == {"value"}
                for tool in ["echo", "async_echo"]:
                    result = await client.call_tool(tool, {"value": '{"café":[]}\r\n'})
                    assert not result.is_error
                    assert result.structured_content == {
                        "value": '{"café":[]}\r\n',
                        "lifecycle": "live",
                    }
                for tool, args, code in [
                    ("echo", {"value": {}}, "argument-invalid"),
                    ("domain", {}, "record-invalid"),
                    ("crash", {}, "internal-error"),
                    ("internal_validation", {}, "internal-error"),
                ]:
                    result = await client.call_tool(tool, args)
                    assert result.is_error
                    assert result.structured_content["type"].endswith("/" + code)
                    assert "Traceback (most recent call last)" not in str(result)
                    if tool == "crash":
                        assert result.structured_content["detail"] == (
                            "knowledge-mcp failed: private diagnostic sentinel. "
                            "Run kb doctor --verbose and report the output at "
                            "https://github.com/SterlingJF/knowledge-mcp/issues."
                        )

    anyio.run(steps)
    assert (tmp_path / "lifecycle").read_text() == "exited"
    stderr = diagnostics.read_text()
    assert "private diagnostic sentinel" in stderr
    assert "InternalArguments" in stderr
    assert len((tmp_path / "log.jsonl").read_text().splitlines()) == 6
