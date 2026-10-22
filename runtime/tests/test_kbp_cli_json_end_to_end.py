from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from mcp.types import CallToolResult

from knowledge_mcp import schemas
from tests.harness import CODEBASE, scope_arguments, session, write
from tests.kb_cli import kb_mcp, run_kb
from tests.test_kb_end_to_end import snapshot
from tests.test_kb_kbp_end_to_end import hidden_package, sample
from tests.test_kbp_tools import streams


@pytest.mark.parametrize(
    ("mode", "argv", "extra"),
    [
        ("validate", [], {}),
        ("self_check", [], {}),
        ("version", [], {}),
        ("inspect", ["--universe", CODEBASE], {"universe": CODEBASE}),
        ("kinds", ["--format", "markdown"], {"format": "markdown"}),
        (
            "card",
            ["readme", "--format", "markdown"],
            {"kind": "readme"},
        ),
    ],
)
@pytest.mark.parametrize("name", ["one", "failing"])
def test_cli_json_matches_actual_mcp_raw_streams_schema_status_and_one_log(
    tmp_path, mode, argv, extra, name
):
    root = sample(tmp_path, name)
    home = tmp_path / "home"
    before = snapshot(root)
    syntax = ["--version"] if mode == "version" else [mode.replace("_", "-")]
    raw = run_kb(home, "kbp", *syntax, *argv, cwd=root)
    done = run_kb(home, "kbp", *syntax, *argv, "--json", cwd=root)
    receipt = CallToolResult.model_validate_json(done.stdout)
    tool = "kbp_" + mode
    Draft202012Validator(schemas.listed(schemas.RESULTS[tool])).validate(
        receipt.structured_content
    )
    assert streams(receipt) == (raw.stdout, raw.stderr, raw.returncode)
    assert done.returncode == raw.returncode
    assert receipt.is_error is (done.returncode != 0)
    assert "Traceback" not in done.stderr
    if done.returncode:
        assert done.stderr.count("Error:") == 1
        assert json.loads(done.stderr.splitlines()[-1]) == receipt.structured_content
    else:
        assert done.stderr == ""
    arguments = (
        {}
        if mode in {"self_check", "version"}
        else {
            **scope_arguments(root, "draft.md", send_text=True),
            "location": str(root / "draft.md"),
            **extra,
        }
    )

    async def call(client):
        return await client.call_tool(tool, arguments)

    answer = session(kb_mcp(tmp_path / "server"), call)
    assert answer.is_error == receipt.is_error
    mcp_out, mcp_err, mcp_code = streams(answer)
    assert (mcp_out, mcp_err, mcp_code) == streams(receipt)
    expected = dict(answer.structured_content)
    expected.pop("note", None)
    assert expected == receipt.structured_content
    assert snapshot(root) == before
    rows = [
        json.loads(line)
        for line in (home / ".local/state/knowledge-mcp/log.jsonl")
        .read_text()
        .splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["tool"] == tool
    assert rows[0]["returned"] == [block.text for block in receipt.content]


def test_explore_json_writes_only_explicit_destination_and_refuses_collision(tmp_path):
    root = sample(tmp_path, "one")
    before = snapshot(root)
    home = tmp_path / "home"
    out = tmp_path / "viewer"
    done = run_kb(home, "kbp", "explore", "--output", str(out), "--json", cwd=root)
    receipt = CallToolResult.model_validate_json(done.stdout)
    assert done.returncode == 0 and not receipt.is_error
    assert (out / "index.html").is_file()

    async def call(client):
        return await client.call_tool(
            "kbp_explore",
            {
                **scope_arguments(root, "draft.md", send_text=True),
                "location": str(root / "draft.md"),
            },
        )

    answer = session(kb_mcp(tmp_path / "server"), call)
    assert not answer.is_error
    direct = json.loads(receipt.structured_content["stdout"])
    remote = json.loads(answer.structured_content["stdout"])
    # Output paths differ because MCP writes into private state, while both
    # viewers must contain the same model, definitions and viewer bundle.
    direct.pop("outputs")
    remote.pop("outputs")
    assert direct == remote
    viewer = Path(answer.structured_content["note"]["explorer"])
    assert (viewer / "index.html").read_bytes() == (out / "index.html").read_bytes()
    written = snapshot(out)
    done = run_kb(home, "kbp", "explore", "--output", str(out), "--json", cwd=root)
    failure = CallToolResult.model_validate_json(done.stdout)
    assert done.returncode == 1 and failure.is_error
    assert failure.structured_content["type"].endswith("/kbp-failed")
    assert json.loads(done.stderr.splitlines()[-1]) == failure.structured_content
    assert snapshot(out) == written
    assert snapshot(root) == before


def test_mint_json_preserves_native_code_shape_without_writing_definitions(tmp_path):
    root = sample(tmp_path, "one")
    before = snapshot(root)
    done = run_kb(tmp_path / "home", "kbp", "mint", "element", "2", "--json", cwd=root)
    receipt = CallToolResult.model_validate_json(done.stdout)
    assert done.returncode == 0 and not receipt.is_error
    codes = receipt.structured_content["stdout"].splitlines()
    assert len(codes) == len(set(codes)) == 2
    assert all(code.startswith("e") and len(code) == len(codes[0]) for code in codes)

    async def call(client):
        return await client.call_tool(
            "kbp_mint",
            {
                **scope_arguments(root, "draft.md", send_text=True),
                "location": str(root / "draft.md"),
                "kind": "element",
                "count": 2,
            },
        )

    answer = session(kb_mcp(tmp_path / "server"), call)
    assert not answer.is_error
    minted = answer.structured_content["stdout"].splitlines()
    assert len(minted) == len(set(minted)) == 2
    assert [(code[0], len(code)) for code in minted] == [
        (code[0], len(code)) for code in codes
    ]
    assert snapshot(root) == before


@pytest.mark.parametrize("mode", ["validate", "explore", "card", "mint"])
def test_help_after_native_args_never_runs_or_writes(tmp_path, mode):
    root = sample(tmp_path, "one")
    out = tmp_path / "unused"
    home = tmp_path / "home"
    before = snapshot(tmp_path)
    for help_flag in ["--help", "-h"]:
        done = run_kb(
            home, "kbp", mode, "--output", str(out), help_flag, "--json", cwd=root
        )
        assert done.returncode == 0 and done.stderr == ""
        assert "Usage:" in done.stdout
        assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "argv",
    [
        ["setup", "codex", "--remov", "--json"],
        ["type", "--hat", "maintainer", "--json"],
        ["kbp", "wrong", "--json"],
    ],
)
def test_invalid_owned_syntax_has_one_coded_error_and_no_writes(tmp_path, argv):
    write(tmp_path, ".codex/config.toml", '# keep\nmodel = "unchanged"\n')
    before = snapshot(tmp_path)
    done = run_kb(tmp_path, *argv)
    assert done.returncode == 2 and done.stdout == ""
    assert done.stderr.count("Error:") == 1 and "Traceback" not in done.stderr
    assert json.loads(done.stderr.splitlines()[-1])["type"].endswith(
        "/argument-invalid"
    )
    assert snapshot(tmp_path) == before


def test_missing_install_json_provides_reinstall_without_traceback_or_writes(tmp_path):
    env = hidden_package(tmp_path)
    before = snapshot(tmp_path)
    done = run_kb(
        tmp_path, "kbp", "validate", "--json", PYTHONDONTWRITEBYTECODE="1", **env
    )
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.count("Error:") == 1 and "Traceback" not in done.stderr
    assert "brew reinstall knowledge-mcp" in done.stderr
    assert json.loads(done.stderr.splitlines()[-1])["type"]
    assert snapshot(tmp_path) == before


def test_actual_mcp_unknown_key_refused_before_explorer_write(tmp_path):
    root = sample(tmp_path, "one")
    before = snapshot(root)
    params = kb_mcp(tmp_path / "server")

    async def call(client):
        return await client.call_tool(
            "kbp_explore",
            {
                **scope_arguments(root, "draft.md", send_text=True),
                "location": str(root / "draft.md"),
                "output": str(tmp_path / "forbidden"),
            },
        )

    answer = session(params, call)
    assert answer.is_error
    assert answer.structured_content["type"].endswith("/argument-invalid")
    assert not (tmp_path / "forbidden").exists()
    assert not (tmp_path / "server/state/knowledge-mcp/explorer").exists()
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "argv", [["validate"], ["explore", "--outpu", "unused"], ["kinds", "--unknown"]]
)
def test_native_failures_keep_json_parseable_with_coded_problem_and_no_writes(
    tmp_path, argv
):
    root = sample(tmp_path, "unparsable")
    home = tmp_path / "home"
    before = snapshot(root)
    done = run_kb(home, "kbp", *argv, "--json", cwd=root)
    assert done.returncode == 1
    receipt = CallToolResult.model_validate_json(done.stdout)
    assert receipt.is_error
    assert receipt.meta["exit_code"] == 1
    assert receipt.structured_content == json.loads(done.stderr.splitlines()[-1])
    assert receipt.structured_content["type"].endswith("/kbp-failed")
    assert done.stderr.count("Error:") == 1 and "Traceback" not in done.stderr
    assert snapshot(root) == before
    assert not (root / "unused").exists()
