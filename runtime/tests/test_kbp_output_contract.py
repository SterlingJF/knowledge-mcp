from __future__ import annotations

import json
import logging
from contextlib import contextmanager

import anyio
import pytest
from jsonschema import Draft202012Validator
from mcp.client import Client
from pydantic import ValidationError, create_model

from knowledge_mcp import kbp, log, problems, schemas, version
from knowledge_mcp.main import Server, build_server
from knowledge_mcp.models_auto.kbp_output_schema import KbpOutputAnswer
from knowledge_mcp.scope import Rebuilt, Workspace
from knowledge_mcp.tools import kbp as tools_kbp
from knowledge_mcp.tools import respond

# Deliberately independent of RESULTS: omitting a mode must fail coverage.
SCOPED = {"location": "supplied document", "folders": [], "knowledge_bus_folders": []}
CASES = [
    ("kbp_validate", SCOPED),
    ("kbp_self_check", {}),
    ("kbp_version", {}),
    ("kbp_mint", {**SCOPED, "kind": "element"}),
    ("kbp_inspect", SCOPED),
    ("kbp_explore", SCOPED),
    ("kbp_kinds", SCOPED),
    ("kbp_card", {**SCOPED, "kind": "design-proposal"}),
    ("kbp_card", {**SCOPED, "kind": "design-proposal", "format": "json"}),
]
BASE = problems.BASE


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))

    @contextmanager
    def rebuilt(_self, _request, *, sent_only=False):
        assert isinstance(sent_only, bool)
        yield Rebuilt(cwd=tmp_path, bundled=["example"], key="a" * 64)

    monkeypatch.setattr(Workspace, "rebuilt", rebuilt)


def call(tool, arguments, mode):
    async def steps():
        async with Client(build_server(), mode=mode) as client:
            listed = {item.name: item for item in (await client.list_tools()).tools}
            result = await client.call_tool(tool, arguments)
            Draft202012Validator(listed[tool].output_schema).validate(
                result.structured_content
            )
            return result

    return anyio.run(steps)


def logged_once(result, tool):
    rows = [json.loads(line) for line in log.path().read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["tool"] == tool
    assert rows[0]["returned"] == [block.text for block in result.content]


@pytest.mark.usefixtures("isolated")
@pytest.mark.parametrize("mode", ["legacy", "auto"])
@pytest.mark.parametrize(("tool", "arguments"), CASES)
@pytest.mark.parametrize("exit_code", [0, 1, -9])
def test_each_mode_preserves_text_and_returns_a_schema_valid_result(
    monkeypatch, tool, arguments, mode, exit_code
):
    # Includes non-JSON text, Unicode, whitespace, and stderr on success.
    output = kbp.Printed("  raw λ\r\n\n", "warning\n", exit_code)
    invoked = []

    def run(argv, _cwd):
        invoked.append(argv)
        return output

    monkeypatch.setattr(kbp, "run", run)
    result = call(tool, arguments, mode)
    assert len(invoked) == 1
    assert result.is_error is (exit_code != 0)
    expected_meta = {"exit_code": exit_code}
    if mode == "auto":
        expected_meta["io.modelcontextprotocol/serverInfo"] = {
            "name": "knowledge-mcp",
            "title": "knowledge-mcp",
            "version": version(),
        }
    assert result.meta == expected_meta
    ordered = [(block.meta["stream"], block.text) for block in result.content]
    assert ordered[:2] == [("stdout", output.stdout), ("stderr", output.stderr)]
    has_note = tool not in ("kbp_self_check", "kbp_version")
    assert [stream for stream, _ in ordered] == ["stdout", "stderr"] + (
        ["knowledge-mcp"] if has_note else []
    )
    blocks = dict(ordered)
    assert blocks["stdout"] == output.stdout
    assert blocks["stderr"] == output.stderr
    assert len(result.content) == len(blocks)  # no synthetic JSON/detail block
    if exit_code:
        invocation = {
            "kbp_validate": "kbp",
            "kbp_self_check": "kbp --self-check",
            "kbp_version": "kbp --version",
            "kbp_mint": "kbp --mint",
            "kbp_inspect": "kbp --inspect",
            "kbp_explore": "kbp --explore",
            "kbp_kinds": "kbp --kinds",
            "kbp_card": "kbp --card",
        }[tool]
        assert result.structured_content == {
            "type": BASE + "kbp-failed",
            "title": "kbp failed",
            "detail": f"{invocation} exited with code {exit_code}.",
        }
    else:
        expected = {
            "schema": "knowledge-mcp/kbp-output/1",
            "stdout": output.stdout,
            "stderr": output.stderr,
            "exit_code": 0,
        }
        if "knowledge-mcp" in blocks:
            expected["note"] = json.loads(blocks["knowledge-mcp"])
        assert result.structured_content == expected
    logged_once(result, tool)


@pytest.mark.usefixtures("isolated")
@pytest.mark.parametrize("mode", ["legacy", "auto"])
@pytest.mark.parametrize(("tool", "arguments"), CASES)
def test_each_mode_refuses_unknown_keys_before_upstream(
    monkeypatch, tool, arguments, mode, caplog
):
    def unexpected(*_args, **_kwargs):
        pytest.fail("upstream ran for an unknown argument")

    monkeypatch.setattr(kbp, "run", unexpected)
    result = call(tool, {**arguments, "unexpected": "private marker"}, mode)
    assert result.is_error
    found = result.structured_content
    assert found["type"] == BASE + "argument-invalid"
    assert [error["pointer"] for error in found["errors"]] == ["#/unexpected"]
    assert "private marker" not in json.dumps(found)
    assert not [record for record in caplog.records if record.exc_info]
    logged_once(result, tool)


@pytest.mark.usefixtures("isolated")
@pytest.mark.parametrize("mode", ["legacy", "auto"])
@pytest.mark.parametrize(("tool", "arguments"), CASES)
@pytest.mark.parametrize("missing", [False, True])
def test_each_mode_codes_upstream_exceptions(  # noqa: PLR0913 - independent mode/error matrix plus diagnostic fixtures.
    monkeypatch, tool, arguments, mode, missing, *, caplog, capsys
):
    def failed(*_args, **_kwargs):
        if missing:
            message = "kbp is missing"
            raise problems.KbpMissing(message)
        message = "failed before returning output"
        raise RuntimeError(message)

    monkeypatch.setattr(kbp, "run", failed)
    result = call(tool, arguments, mode)
    assert result.is_error
    assert result.structured_content["type"] == BASE + (
        "kbp-failed" if missing else "internal-error"
    )
    diagnostics = [record for record in caplog.records if record.exc_info]
    assert len(diagnostics) == (0 if missing else 1)
    if not missing:
        record = diagnostics[0]
        assert record.name == "knowledge_mcp.main"
        assert record.levelno == logging.ERROR
        assert isinstance(record.exc_info[1].__cause__, RuntimeError)
        assert "failed before returning output" in caplog.text
        assert "Traceback" in caplog.text
    assert "Traceback" not in result.model_dump_json()
    assert "Traceback" not in log.path().read_text()
    assert "Traceback" not in capsys.readouterr().out
    logged_once(result, tool)


@pytest.mark.usefixtures("isolated")
def test_nested_unknown_key_is_refused_before_upstream(monkeypatch, caplog):
    def unexpected(*_args, **_kwargs):
        pytest.fail("upstream ran for a nested unknown argument")

    monkeypatch.setattr(kbp, "run", unexpected)
    result = call(
        "kbp_kinds",
        {**SCOPED, "knowledge_bus_folders": [{"folder": "", "extra": True}]},
        "legacy",
    )
    assert result.is_error
    assert result.structured_content["type"] == BASE + "argument-invalid"
    assert result.structured_content["errors"][0]["pointer"].endswith("/extra")
    assert not [record for record in caplog.records if record.exc_info]
    logged_once(result, "kbp_kinds")


@pytest.mark.usefixtures("isolated")
@pytest.mark.parametrize("mode", ["legacy", "auto"])
@pytest.mark.parametrize("format", ["", "JSON", "yaml", False, 1, [], {}])
def test_card_invalid_format_is_refused_before_upstream(monkeypatch, mode, format):
    def unexpected(*_args, **_kwargs):
        pytest.fail("upstream ran for an invalid card format")

    monkeypatch.setattr(kbp, "run", unexpected)
    result = call(
        "kbp_card", {**SCOPED, "kind": "design-proposal", "format": format}, mode
    )
    assert result.is_error
    assert result.structured_content["type"] == BASE + "argument-invalid"
    assert result.structured_content["errors"][0]["pointer"] == "#/format"
    logged_once(result, "kbp_card")


@pytest.mark.parametrize("stdout", ["", "not JSON\n", '{"schema":"future/99"}'])
def test_adapter_handles_empty_and_opaque_success(monkeypatch, stdout):
    records = []
    monkeypatch.setattr(log, "record", lambda *args: records.append(args))
    result = respond.printed("kbp_version", "", {}, kbp.Printed(stdout, "", 0))
    assert result.structured_content["stdout"] == stdout
    assert [block.text for block in result.content] == ([stdout] if stdout else [])
    assert len(records) == 1


def test_generated_model_and_listed_schema_enforce_the_success_contract():
    schema = schemas.listed("kbp-output")
    validator = Draft202012Validator(schema)
    good = {
        "schema": "knowledge-mcp/kbp-output/1",
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
    }
    validator.validate(good)
    KbpOutputAnswer.model_validate(good)
    bad = [
        {key: value for key, value in good.items() if key != "stdout"},
        {**good, "extra": True},
        {**good, "exit_code": 1},
        {**good, "schema": "other/1"},
        {**good, "stdout": []},
        {**good, "note": {"extra": True}},
    ]
    for data in bad:
        assert not validator.is_valid(data), data
        with pytest.raises(ValidationError):
            KbpOutputAnswer.model_validate(data)


def test_bad_receipt_fails_before_logging(monkeypatch):
    records = []
    monkeypatch.setattr(log, "record", lambda *args: records.append(args))
    with pytest.raises(ValidationError):
        respond.printed(
            "kbp_version", "", {}, kbp.Printed("ok", "", 0), {"extra": True}
        )
    assert records == []


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("validate", "kbp exited with code 1."),
        ("self_check", "kbp --self-check exited with code 1."),
        ("kinds", "kbp --kinds exited with code 1."),
        ("inspect", "kbp --inspect exited with code 1."),
        ("card", "kbp --card exited with code 1."),
    ],
)
def test_failure_invocation_labels_are_literal(mode, expected):
    output = kbp.Printed("raw stdout", "raw stderr", 1)
    failure = problems.KbpFailed(output, mode)
    assert failure.detail == expected
    assert failure.output is output
    assert failure.code == "kbp-failed"


@pytest.mark.usefixtures("isolated")
@pytest.mark.parametrize("mode", ["legacy", "auto"])
def test_bad_output_receipt_is_internal_with_server_diagnostics(
    monkeypatch, mode, caplog, capsys
):
    monkeypatch.setattr(kbp, "run", lambda *_args: kbp.Printed("raw", "warning", 0))
    monkeypatch.setattr(tools_kbp, "note", lambda *_args: {"extra": True})
    result = call("kbp_validate", SCOPED, mode)
    assert result.is_error
    assert result.structured_content["type"] == BASE + "internal-error"
    diagnostics = [record for record in caplog.records if record.exc_info]
    assert len(diagnostics) == 1
    assert diagnostics[0].name == "knowledge_mcp.main"
    assert diagnostics[0].levelno == logging.ERROR
    assert isinstance(diagnostics[0].exc_info[1].__cause__, ValidationError)
    assert "Traceback" in caplog.text
    assert "Traceback" not in result.model_dump_json()
    assert "Traceback" not in log.path().read_text()
    assert "Traceback" not in capsys.readouterr().out
    logged_once(result, "kbp_validate")


@pytest.mark.usefixtures("isolated")
def test_unexpected_validation_is_not_classified_by_arguments_title(
    monkeypatch, caplog
):
    receipt = create_model("ReceiptArguments", value=(int, ...))

    def failed(*_args, **_kwargs):
        receipt.model_validate({"value": "invalid"})

    monkeypatch.setattr(kbp, "run", failed)
    result = call("kbp_version", {}, "legacy")
    assert result.structured_content["type"] == BASE + "internal-error"
    assert len([record for record in caplog.records if record.exc_info]) == 1
    logged_once(result, "kbp_version")


@pytest.mark.usefixtures("isolated")
def test_expected_problem_has_no_traceback(monkeypatch, caplog):
    def failed(*_args, **_kwargs):
        message = "Invalid scope."
        raise problems.Error(message, code="scope-invalid")

    monkeypatch.setattr(kbp, "run", failed)
    result = call("kbp_version", {}, "legacy")
    assert result.structured_content["type"] == BASE + "scope-invalid"
    assert not [record for record in caplog.records if record.exc_info]
    logged_once(result, "kbp_version")


@pytest.mark.parametrize("name", sorted(schemas.RESULTS))
def test_app_tool_missing_canonical_schema_is_rejected(monkeypatch, name):
    monkeypatch.delitem(schemas.RESULTS, name)
    with pytest.raises(ValueError, match="App tools missing canonical result schemas"):
        build_server()


@pytest.mark.parametrize("mode", ["legacy", "auto"])
def test_registered_sdk_extension_keeps_native_schema_and_raw_text(mode):
    server = Server(name="sdk-extension")

    @server.tool(title="Native echo")
    def echo(value: str | None = None) -> dict[str, str | None]:
        return {"value": value}

    native = server.tools.get_tool("echo")
    assert native is not None
    assert "echo" not in schemas.RESULTS

    async def steps():
        async with Client(server, mode=mode) as client:
            listed = (await client.list_tools()).tools
            assert len(listed) == 1
            assert listed[0].output_schema == native.output_schema
            assert listed[0].title == "Native echo"
            for value in [None, "null", "false", "0", '{"a":1}', " \tλ\r\n"]:
                result = await client.call_tool("echo", {"value": value})
                assert not result.is_error
                assert result.structured_content == {"value": value}

    anyio.run(steps)
