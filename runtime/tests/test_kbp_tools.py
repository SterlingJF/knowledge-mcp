from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.client import Client

from knowledge_mcp.main import build_server
from knowledge_mcp.models import ScopeRequest
from knowledge_mcp.scope import Workspace
from tests.harness import (
    CODEBASE,
    PRODUCT,
    knowledge_base,
    scope_arguments,
    server_parameters,
    session,
    texts,
    write,
)
from tests.kb_cli import KBP, kbp_env

RFC = "docs/rfcs/0042-cache.md"
RECORD = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"


@pytest.fixture(autouse=True)
def state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path / "state"


@pytest.fixture
def codebase(tmp_path: Path) -> Path:
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC, "# Cache\n")
    return root


def in_process(workspace: Workspace, calls: list[tuple[str, dict[str, Any]]]) -> list:
    async def main():
        async with Client(build_server(workspace), mode="legacy") as client:
            return [
                await client.call_tool(name, arguments) for name, arguments in calls
            ]

    return anyio.run(main)


def printed(
    workspace: Workspace, arguments: dict[str, Any], argv: list[str], **env: str
):
    request = ScopeRequest.model_validate(arguments)
    with workspace.rebuilt(request) as rebuilt:
        done = subprocess.run(
            [str(KBP), *argv],
            cwd=rebuilt.cwd,
            capture_output=True,
            text=True,
            check=False,
            env=kbp_env(**env),
        )
    return done.stdout, done.stderr, done.returncode


def streams(result) -> tuple[str, str, int]:
    out = "".join(
        b.text for b in result.content if (b.meta or {}).get("stream") == "stdout"
    )
    err = "".join(
        b.text for b in result.content if (b.meta or {}).get("stream") == "stderr"
    )
    return out, err, result.meta["exit_code"]


CASES = [
    ("kbp_validate", {}, [], True),
    ("kbp_inspect", {"universe": PRODUCT}, ["--inspect", "--universe", PRODUCT], False),
    ("kbp_kinds", {}, ["--kinds"], False),
    ("kbp_kinds", {"format": "markdown"}, ["--kinds", "--format", "markdown"], False),
    (
        "kbp_card",
        {"kind": "design-proposal", "universe": CODEBASE},
        ["--card", "design-proposal", "--universe", CODEBASE, "--format", "markdown"],
        False,
    ),
    (
        "kbp_card",
        {"kind": "no-such-type", "universe": CODEBASE},
        ["--card", "no-such-type", "--universe", CODEBASE, "--format", "markdown"],
        False,
    ),
]


@pytest.mark.parametrize("case", CASES)
def test_kbp_tool_matches_cli_streams_and_exit_status(codebase, tmp_path, case):
    tool, extra, argv, send_text = case
    workspace = Workspace(tmp_path / "work")
    arguments = {
        **scope_arguments(codebase, RFC, send_text=send_text),
        "location": str(codebase / RFC),
        **extra,
    }

    [result] = in_process(workspace, [(tool, arguments)])

    scope = {key: arguments[key] for key in ("folders", "knowledge_bus_folders")}
    assert streams(result) == printed(workspace, scope, argv)
    assert result.is_error is (result.meta["exit_code"] != 0)


def test_mint_matches_cli_code_shape_and_count(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {
        **scope_arguments(codebase, RFC),
        "location": str(codebase / RFC),
        "kind": "element",
        "count": 3,
    }

    [result] = in_process(workspace, [("kbp_mint", arguments)])

    scope = {key: arguments[key] for key in ("folders", "knowledge_bus_folders")}
    out, err, code = streams(result)
    kbp_out, kbp_err, kbp_code = printed(workspace, scope, ["--mint", "element", "3"])
    # Random codes prevent comparisons of exact output.
    shape = [(line[0], len(line)) for line in out.splitlines()]
    assert shape == [(line[0], len(line)) for line in kbp_out.splitlines()]
    assert len(shape) == 3
    assert (err, code) == (kbp_err, kbp_code) == ("", 0)


def test_version_and_self_check_match_cli_output(tmp_path):
    workspace = Workspace(tmp_path / "work")
    version, self_check = in_process(
        workspace, [("kbp_version", {}), ("kbp_self_check", {})]
    )

    for result, argv in ((version, ["--version"]), (self_check, ["--self-check"])):
        done = subprocess.run(
            [str(KBP), *argv], capture_output=True, text=True, check=False
        )
        assert streams(result) == (done.stdout, done.stderr, done.returncode)


def test_explore_writes_index_and_returns_explorer_path(codebase, state):
    arguments = {
        **scope_arguments(codebase, RFC),
        "location": str(codebase / RFC),
        "universe": PRODUCT,
    }

    async def steps(client):
        return await client.call_tool("kbp_explore", arguments)

    result = session(server_parameters(state), steps)

    assert not result.is_error, texts(result)
    out, _, code = streams(result)
    assert code == 0
    receipt = json.loads(out)
    assert receipt["universe"]["id"] == PRODUCT
    [written] = list((state / "knowledge-mcp" / "explorer").iterdir())
    assert (written / "index.html").is_file()
    assert str(written) in texts(result)[-1]


def test_validate_rejects_bundled_copies(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {**scope_arguments(codebase, RFC), "location": str(codebase / RFC)}

    [result] = in_process(workspace, [("kbp_validate", arguments)])

    assert result.is_error
    assert "Send the text" in texts(result)[0]


def test_check_runs_on_text_sent_earlier_by_digest(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    first = {
        **scope_arguments(codebase, RFC, send_text=True),
        "location": str(codebase / RFC),
    }
    [checked] = in_process(workspace, [("kbp_validate", first)])
    digests = json.loads(texts(checked)[-1])["received"]
    by_name = {item["name"]: item["digest"] for item in digests}
    second = json.loads(json.dumps(first))
    for scope in second["knowledge_bus_folders"]:
        for entry in scope["files"]:
            del entry["text"]
            entry["digest"] = by_name[entry["name"]]

    [again] = in_process(workspace, [("kbp_validate", second)])

    assert streams(again) == streams(checked)
    assert again.meta["exit_code"] == 0


def test_unknown_spec_digest_returns_text_request(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")
    arguments = {**scope_arguments(codebase, RFC), "location": str(codebase / RFC)}
    arguments["knowledge_bus_folders"][0]["files"][0] |= {
        "id": "mine",
        "digest": "sha256:00",
    }

    [result] = in_process(workspace, [("kbp_kinds", arguments)])

    assert result.is_error
    assert "Send the text of" in texts(result)[0]


def test_validate_ignores_document_types_plugin_directory(codebase, tmp_path):
    workspace = Workspace(tmp_path / "work")

    def check_both() -> tuple[tuple[str, str, int], tuple[str, str, int]]:
        arguments = {
            **scope_arguments(codebase, RFC, send_text=True),
            "location": str(codebase / RFC),
        }
        [result] = in_process(workspace, [("kbp_validate", arguments)])
        done = subprocess.run(
            [str(KBP)],
            cwd=codebase / "docs" / "rfcs",
            capture_output=True,
            text=True,
            check=False,
            env=kbp_env(),
        )
        return streams(result), (done.stdout, done.stderr, done.returncode)

    without = check_both()
    write(codebase, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    with_record = check_both()

    assert with_record == without
    assert without[0][2] == 0 and without[1][2] == 0


def test_validate_document_types_only_scope_preserves_error(tmp_path):
    root = tmp_path / "plain"
    write(root, RFC, "# Cache\n")
    workspace = Workspace(tmp_path / "work")

    def check() -> tuple[bool, list[str]]:
        arguments = {**scope_arguments(root, RFC), "location": str(root / RFC)}
        [result] = in_process(workspace, [("kbp_validate", arguments)])
        return result.is_error, texts(result)

    without = check()
    write(root, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    assert scope_arguments(root, RFC)["knowledge_bus_folders"] == [
        {"folder": "", "files": []}
    ]
    with_record = check()

    assert with_record[0] and with_record == without


def test_missing_parent_definitions_preserve_kbp_error(
    tmp_path,
):
    root = tmp_path / "plain"
    write(root, RECORD, "schema: knowledge-mcp/document-types/1\nfiles: {}\n")
    write(root, "team/.knowledge-bus/workspace.yaml", f"from_parent:\n  - {PRODUCT}\n")
    document = "team/notes/pricing.md"
    write(root, document, "# Pricing\n")
    workspace = Workspace(tmp_path / "work")
    scope = scope_arguments(root, document)
    assert scope["knowledge_bus_folders"] == [
        {"folder": "", "files": []},
        {
            "folder": "team",
            "files": [],
            "workspace_yaml": f"from_parent:\n  - {PRODUCT}\n",
        },
    ]
    located = {**scope, "location": str(root / document)}

    fitted, listed = in_process(
        workspace,
        [
            ("kb_get_document_type", {**located, "name": "pricing.md"}),
            ("kbp_kinds", located),
        ],
    )

    done = subprocess.run(
        [str(KBP), "--kinds"],
        cwd=root / "team" / "notes",
        capture_output=True,
        text=True,
        check=False,
        env=kbp_env(),
    )
    direct = (done.stdout, done.stderr, done.returncode)
    assert done.returncode == 1
    assert json.loads(done.stderr)["schema"] == "knowledge-bus/inspection-error/1"
    assert "from_parent" in json.loads(done.stderr)["message"]
    assert fitted.is_error and listed.is_error
    assert streams(fitted) == direct
    assert streams(listed) == direct
