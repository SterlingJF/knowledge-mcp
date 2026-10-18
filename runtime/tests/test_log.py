from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from knowledge_mcp import log
from tests.harness import (
    CODEBASE,
    MODULE,
    PRODUCT,
    knowledge_base,
    scope_arguments,
    server_parameters,
    session,
    texts,
    type_arguments,
    write,
)

RFC = "docs/rfcs/0042-cache.md"


def entries(state: Path) -> list[dict]:
    log = state / "knowledge-mcp" / "log.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_every_returned_text_appears_once_in_the_log(tmp_path):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC)
    scope = {**scope_arguments(root, RFC), "location": str(root / RFC)}
    calls = [
        ("kb_get_document_type", type_arguments(root, RFC)),
        (
            "kb_get_document_type",
            type_arguments(root, RFC, location="notion://page/abc"),
        ),
        ("kbp_kinds", scope),
        ("kbp_card", {**scope, "kind": "design-doc", "universe": PRODUCT}),
        ("kbp_card", {**scope, "kind": "not-a-type"}),
        ("kbp_version", {}),
    ]
    state = tmp_path / "state"

    async def steps(client):
        return [await client.call_tool(name, arguments) for name, arguments in calls]

    results = session(server_parameters(state), steps)
    logged = entries(state)

    assert [entry["tool"] for entry in logged] == [name for name, _ in calls]
    assert [entry["returned"] for entry in logged] == [texts(r) for r in results]
    every = [text for entry in logged for text in entry["returned"]]
    for result in results:
        for text in texts(result):
            assert every.count(text) == sum(texts(r).count(text) for r in results)
    assert [entry["location"] for entry in logged] == [
        str(root / RFC),
        "notion://page/abc",
        str(root / RFC),
        str(root / RFC),
        str(root / RFC),
        "",
    ]
    for entry, (_, arguments) in zip(logged, calls, strict=True):
        canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
        assert (
            entry["sent"] == "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
        )
        assert entry["time"].endswith("Z")


def test_log_uses_home_state_directory_without_overrides(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "PATH": os.environ["PATH"],
        "USER": os.environ.get("USER", "someone"),
        "TMPDIR": str(tmp_path),
    }
    script = "from knowledge_mcp import log; log.record('kbp_version', '', {}, ['x']); print(log.path())"

    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=MODULE,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    path = home / ".local" / "state" / "knowledge-mcp" / "log.jsonl"
    assert done.stdout.strip() == str(path)
    assert json.loads(path.read_text())["returned"] == ["x"]
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_state_directory_prefers_override_then_xdg_then_home(tmp_path):

    home = tmp_path / "home"
    chosen = tmp_path / "my history"
    xdg = tmp_path / "xdg state"
    both = {"KNOWLEDGE_MCP_STATE_DIR": str(chosen), "XDG_STATE_HOME": str(xdg)}

    assert log.directory(both, home) == chosen
    assert log.directory({"XDG_STATE_HOME": str(xdg)}, home) == xdg / "knowledge-mcp"
    assert log.directory({}, home) == home / ".local" / "state" / "knowledge-mcp"
    relative = {"KNOWLEDGE_MCP_STATE_DIR": "history", "XDG_STATE_HOME": "state"}
    assert log.directory(relative, home) == home / ".local" / "state" / "knowledge-mcp"


def test_explicit_state_directory_controls_log_path(tmp_path):
    chosen = tmp_path / "my history"
    env = {
        "HOME": str(tmp_path / "home"),
        "PATH": os.environ["PATH"],
        "KNOWLEDGE_MCP_STATE_DIR": str(chosen),
        "XDG_STATE_HOME": str(tmp_path / "xdg"),
    }
    script = "from knowledge_mcp import log; log.record('kbp_version', '', {}, ['x']); print(log.path())"

    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=MODULE,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert done.stdout.strip() == str(chosen / "log.jsonl")
    assert json.loads((chosen / "log.jsonl").read_text())["returned"] == ["x"]
    assert not (tmp_path / "xdg").exists()
