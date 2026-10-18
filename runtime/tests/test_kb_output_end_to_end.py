from __future__ import annotations

import json
import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.harness import (
    CODEBASE,
    MODULE,
    knowledge_base,
    session,
    type_arguments,
    write,
)
from tests.kb_cli import HARNESSES, kb_mcp, run_kb
from tests.test_approved_names_end_to_end import design_proposal, document_types_file
from tests.test_kb_end_to_end import DESKTOP, entry, fixture_home, snapshot

TITLES = dict(
    zip(
        HARNESSES,
        ["Claude Code", "Codex", "Claude desktop app", "Pi", "OpenCode"],
        strict=True,
    )
)
CONFIGS = dict(
    zip(
        HARNESSES,
        [
            ".claude.json",
            ".codex/config.toml",
            DESKTOP,
            ".pi/agent/mcp.json",
            ".config/opencode/opencode.json",
        ],
        strict=True,
    )
)


def live(home, *args, **env):
    # Use the worktree executable so doctor can verify the command path.
    return run_kb(
        home,
        *args,
        KNOWLEDGE_MCP_COMMAND=str(Path(sys.executable).parent / "kb"),
        **env,
    )


@pytest.mark.parametrize(
    ("argv", "code", "help_command"),
    [
        (["setpu"], 2, "kb --help"),
        (["doctor", "--quiet"], 2, "kb doctor --help"),
        (["type", "/nope/x.md"], 2, "kb type --help"),
        (["setup", "nosuch"], 2, "kb setup --help"),
    ],
)
def test_error_first_then_runnable_help(tmp_path, argv, code, help_command):
    done = live(tmp_path, *argv)
    assert done.returncode == code
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert lines[0].startswith("Error: ") and lines[0].endswith(".")
    assert help_command in lines[-1]
    assert "Usage:" not in done.stderr


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["--version"],
        ["doctor"],
        ["setup", "--help"],
        ["type", "--help"],
        ["mcp", "--help"],
        ["kbp", "--help"],
        ["setpu"],
    ],
)
def test_relative_state_warns_on_every_command(tmp_path, argv):
    done = live(tmp_path, *argv, KNOWLEDGE_MCP_STATE_DIR="state")
    expected = f"Warning: KNOWLEDGE_MCP_STATE_DIR=state is not an absolute path, so kb uses {tmp_path}/.local/state/knowledge-mcp."
    assert expected in done.stderr.splitlines()


@pytest.mark.parametrize("leaf", ["mcp", "setup", "type", "doctor"])
def test_leaf_help_has_examples_side_effects_and_exit_codes(tmp_path, leaf):
    done = live(tmp_path, leaf, "--help")
    assert done.returncode == 0 and done.stderr == ""
    assert done.stdout.startswith(f"Usage: kb {leaf}")
    for text in ["Examples:", "Flags:", "Exit codes:"]:
        assert text in done.stdout
    assert "`" not in done.stdout
    if leaf == "type":
        assert (
            "log.jsonl" in done.stdout
            and "TYPE SPEC MATCHED-BY USED-BY TITLE" in done.stdout
        )
    if leaf == "setup":
        assert "kb backs up existing settings files" in " ".join(done.stdout.split())
    if leaf == "doctor":
        assert "changes no file" in done.stdout


@pytest.mark.parametrize("harness", HARNESSES)
def test_setup_feedback_repeat_and_remove(tmp_path, harness):
    home = fixture_home(tmp_path)
    before = snapshot(home)
    added = live(home, "setup", harness)
    assert added.returncode == 0 and added.stdout == ""
    assert (
        f"Registered knowledge-mcp with {TITLES[harness]} in {home / CONFIGS[harness]}; backup at "
        in added.stderr
    )
    assert "Start a new " in added.stderr or "Restart the " in added.stderr
    assert entry(home, harness)
    recorded = snapshot(home)
    again = live(home, "setup", harness)
    assert again.returncode == 0 and again.stdout == ""
    assert (
        f"kb setup already registered knowledge-mcp with {TITLES[harness]}. Nothing changed."
        in again.stderr
    )
    assert f"kb setup --remove {harness}, then kb setup {harness}." in again.stderr
    assert snapshot(home) == recorded
    removed = live(home, "setup", "--remove", harness)
    assert removed.returncode == 0 and removed.stdout == ""
    assert "Removed the setup record for " in removed.stderr
    assert "Kept " not in removed.stderr
    assert snapshot(home) == before
    absent = live(home, "setup", "--remove", harness)
    assert absent.returncode == 0 and absent.stdout == ""
    assert (
        f"kb did not register knowledge-mcp with {TITLES[harness]}. Nothing changed."
        in absent.stderr
    )


@pytest.mark.parametrize("harness", HARNESSES)
def test_absent_harness_warns_and_still_writes(tmp_path, harness):
    home = tmp_path / "home"
    (home / DESKTOP).parent.mkdir(parents=True)
    done = live(home, "setup", harness)
    assert done.returncode == 0 and done.stdout == ""
    if harness == "claude-desktop" and Path("/Applications/Claude.app").exists():
        assert "to use the knowledge-mcp entry" not in done.stderr
        assert entry(home, harness)
        return
    assert (
        f"Install {TITLES[harness]} to use the knowledge-mcp entry in {home / CONFIGS[harness]}."
        in done.stderr
    )
    assert entry(home, harness)


def test_desktop_zip_command_uses_runtime_skills_in_a_subshell(tmp_path):
    done = live(fixture_home(tmp_path), "setup", "claude-desktop")
    [line] = [line for line in done.stderr.splitlines() if line.startswith("mkdir -p ")]
    assert "(cd " in line and str(MODULE / "skills") in line
    assert "for d in */; do zip -qr " in line
    assert "~/Downloads/knowledge-mcp-skills/" in line
    assert (
        "Upload each ZIP in ~/Downloads/knowledge-mcp-skills through Customize → Skills in Claude."
        in done.stderr
    )


def test_doctor_status_verbose_json_and_fault(tmp_path):
    home = fixture_home(tmp_path)
    default = live(home, "doctor")
    assert default.returncode == 0 and default.stderr == ""
    assert default.stdout.startswith("Install: ")
    assert "No problems found." in default.stdout
    assert (
        "To register knowledge-mcp, run kb setup with claude-code, codex, claude-desktop, pi "
        "or opencode." in default.stdout
    )
    for title in TITLES.values():
        assert f"{title}:  not registered" in default.stdout
    verbose = live(home, "doctor", "--verbose")
    assert verbose.stdout.startswith(default.stdout.rstrip() + "\n")
    for text in [
        "Bundled spec files",
        "Bundled skills",
        "State directory:",
        "kbp:",
        "Release: v",
    ]:
        assert text in verbose.stdout
    live(home, "setup", "codex")
    healthy = live(home, "doctor", "--json")
    data = json.loads(healthy.stdout)
    assert healthy.returncode == 0
    assert set(data) == {
        "schema",
        "kb",
        "knowledge_bus",
        "checks",
        "registrations",
        "problems",
        "warnings",
        "state_dir",
    }
    assert data["schema"] == "knowledge-mcp/doctor/1"
    assert data["problems"] == []
    regs = {r["name"]: r for r in data["registrations"]}
    assert regs["codex"]["status"] == "registered" and regs["codex"]["skills"] == 9
    assert regs["claude-desktop"]["skills"] is None
    (home / ".codex/config.toml").unlink()
    fault = live(home, "doctor")
    assert fault.returncode == 1
    assert "Found 1 problem and 0 warnings." in fault.stdout
    lines = fault.stderr.splitlines()
    assert lines[0].startswith("Error: Codex:")
    assert "kb setup --remove codex, then kb setup codex." in lines[1]
    machine = live(home, "doctor", "--json")
    assert machine.returncode == 1
    assert set(json.loads(machine.stdout)["problems"][0]) == {"message", "fix"}
    problem = json.loads(machine.stderr.splitlines()[-1])
    assert {"type", "title", "detail"} <= problem.keys()


def test_doctor_warning_alone_exits_zero(tmp_path):
    home = fixture_home(tmp_path)
    live(home, "setup", "codex")
    with (home / ".codex/config.toml").open("a") as stream:
        stream.write('\n[plugins."knowledge-mcp@knowledge-mcp"]\nenabled = true\n')
    done = live(home, "doctor", "--json")
    assert done.returncode == 0
    data = json.loads(done.stdout)
    assert data["problems"] == [] and data["warnings"]
    assert set(data["warnings"][0]) == {"message", "fix"}
    assert "Warning: Codex has both the knowledge-mcp entry in" in done.stderr
    assert "kb setup --remove codex" in done.stderr


def output_pty(home, args, *, interrupt=False):
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        [sys.executable, "-m", "knowledge_mcp.cli", *args],
        cwd=MODULE,
        env={
            **os.environ,
            "HOME": str(home),
            "KNOWLEDGE_MCP_STATE_DIR": str(home / "state"),
            "PATH": "",
        },
        stdin=slave if interrupt else subprocess.DEVNULL,
        stdout=subprocess.PIPE if interrupt else slave,
        stderr=subprocess.PIPE,
        text=True,
    )
    os.close(slave)
    try:
        if interrupt:
            assert select.select([proc.stderr], [], [], 8)[0], (
                "server printed no terminal hint"
            )
            hint = proc.stderr.readline()
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "interrupt-test", "version": "1"},
                },
            }
            os.write(master, (json.dumps(request) + "\n").encode())
            assert select.select([proc.stdout], [], [], 8)[0], (
                "server did not initialize"
            )
            response = json.loads(proc.stdout.readline())
            assert response["id"] == 1 and "result" in response
            os.write(
                master, b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
            )
            os.write(master, b'{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
            assert select.select([proc.stdout], [], [], 8)[0], (
                "server did not list tools"
            )
            assert json.loads(proc.stdout.readline())["result"]["tools"]
            started = time.monotonic()
            proc.send_signal(signal.SIGINT)
            stdout, stderr = proc.communicate(timeout=2)
            assert time.monotonic() - started < 2
            return proc.returncode, stdout, hint + stderr
        chunks = []
        while select.select([master], [], [], 8)[0]:
            try:
                block = os.read(master, 65536)
            except OSError:
                break
            if not block:
                break
            chunks.append(block)
        _, stderr = proc.communicate(timeout=8)
        return proc.returncode, b"".join(chunks).decode().replace("\r\n", "\n"), stderr
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)


def test_type_table_pipe_terminal_json_and_mcp_share_the_answer(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    path = write(root, "docs/rfcs/design-proposal.md", "# Cache\n")
    home = tmp_path / "home"
    home.mkdir()
    args = ["type", str(path), "--role", "maintainer"]
    machine = live(home, *args, "--json")
    assert machine.returncode == 0, machine.stderr
    answer = json.loads(machine.stdout)

    async def steps(client):
        listed = {t.name: t for t in (await client.list_tools()).tools}
        result = await client.call_tool(
            "kb_get_document_type",
            {
                **type_arguments(root, "docs/rfcs/design-proposal.md"),
                "role": "maintainer",
            },
        )
        assert not result.is_error
        Draft202012Validator(listed["kb_get_document_type"].output_schema).validate(
            answer
        )
        assert result.structured_content == answer

    session(kb_mcp(tmp_path / "server"), steps)
    pipe = live(home, *args)
    code, terminal, stderr = output_pty(home, args)
    assert code == 0 and stderr == ""
    assert terminal.splitlines()[0].split() == [
        "TYPE",
        "SPEC",
        "MATCHED-BY",
        "USED-BY",
        "TITLE",
    ]
    rows = [line.split("\t") for line in pipe.stdout.splitlines()]
    assert len(rows) == len(answer["candidates"])
    assert all(len(row) == 5 for row in rows)
    for row, item in zip(rows, answer["candidates"], strict=True):
        assert row == [
            item["document_type"],
            item["universe_spec"],
            item["matched_on"],
            item["actor"] or "<unset>",
            item["name"],
        ]
        assert item["document_type"] in terminal
    assert (home / ".local/state/knowledge-mcp/log.jsonl").is_file()


def test_no_filename_match_lists_all_types_and_warns(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    done = live(tmp_path / "home", "type", str(root / "zzzz.unknown"))
    assert done.returncode == 0 and "\t" in done.stdout
    assert (
        "No document type matches the file name zzzz.unknown, so kb lists every document type."
        in done.stderr
    )


def test_json_usage_failure_ends_with_problem_details(tmp_path):
    done = live(tmp_path, "type", "--json", "/nope/x.md")
    assert done.returncode == 2 and done.stdout == ""
    assert done.stderr.startswith("Error: ")
    problem = json.loads(done.stderr.splitlines()[-1])
    assert {"type", "title", "detail"} <= problem.keys()


def test_mcp_terminal_hint_and_interrupt(tmp_path):
    code, stdout, stderr = output_pty(tmp_path, ["mcp"], interrupt=True)
    assert code == 0
    assert stdout == ""
    assert stderr.splitlines() == [
        "kb mcp serves MCP on stdin and stdout for a harness. To connect a harness, run kb setup <harness>. Ctrl-C stops the server."
    ]


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_builtin_completion_sources_and_harness_values(tmp_path, shell):
    source = live(
        tmp_path, path="/opt/homebrew/bin:/usr/bin:/bin", _KB_COMPLETE=f"{shell}_source"
    )
    assert source.returncode == 0 and "kb" in source.stdout and source.stderr == ""
    if shell == "bash":
        result = live(
            tmp_path,
            _KB_COMPLETE="bash_complete",
            COMP_WORDS="kb setup co",
            COMP_CWORD="2",
        )
        assert "codex" in result.stdout
    if shell == "zsh":
        result = live(
            tmp_path,
            _KB_COMPLETE="zsh_complete",
            COMP_WORDS="kb setup co",
            COMP_CWORD="2",
        )
        assert "codex" in result.stdout


@pytest.mark.parametrize("env", [{}, {"NO_COLOR": "1"}])
def test_help_has_no_color_on_a_pipe(tmp_path, env):
    done = live(tmp_path, "--help", **env)
    assert done.returncode == 0 and "\x1b[" not in done.stdout


def test_setup_repeat_leaves_a_missing_entry_for_doctor_to_report(tmp_path):
    home = fixture_home(tmp_path)
    live(home, "setup", "codex")
    config = home / ".codex/config.toml"
    config.unlink()
    before = snapshot(home)
    again = live(home, "setup", "codex")
    assert again.returncode == 0 and "Nothing changed" in again.stderr
    assert snapshot(home) == before
    doctor = live(home, "doctor", "--json")
    assert doctor.returncode == 1
    assert json.loads(doctor.stdout)["problems"]


def test_unrecorded_registration_is_preserved_and_names_removal(tmp_path):
    home = fixture_home(tmp_path)
    config = home / ".codex/config.toml"
    config.write_text(
        config.read_text()
        + '\n[mcp_servers.knowledge-mcp]\ncommand = "kb"\nargs = ["mcp"]\n'
    )
    before = snapshot(home)
    done = live(home, "setup", "--remove", "codex")
    assert done.returncode == 0 and done.stdout == ""
    assert "Nothing changed" in done.stderr
    assert (
        f"{config} has a knowledge-mcp entry that kb did not add. Remove the entry with codex mcp remove knowledge-mcp."
        in done.stderr
    )
    assert snapshot(home) == before


def test_outside_root_and_invalid_yaml_name_the_next_command(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    path = root / "README.md"
    other = tmp_path / "other"
    other.mkdir()
    outside = live(tmp_path / "home", "type", str(path), "--root", str(other))
    assert outside.returncode == 2 and outside.stdout == ""
    assert f"{path} is outside {other}, the folder given with --root." in outside.stderr
    assert "Pass a --root folder that holds the file, or drop --root." in outside.stderr
    record = write(
        root, ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml", "files: [\n"
    )
    broken = live(tmp_path / "home", "type", "--json", str(path))
    assert broken.returncode == 1 and broken.stdout == ""
    assert str(record) in broken.stderr and "is not valid YAML: line" in broken.stderr
    assert f"kb type {path} again." in broken.stderr
    assert json.loads(broken.stderr.splitlines()[-1])["type"].endswith(
        "/record-invalid"
    )


def test_mcp_extra_argument_uses_the_same_error_shape(tmp_path):
    done = live(tmp_path, "mcp", "extra")
    assert done.returncode == 2 and done.stdout == ""
    assert done.stderr.splitlines()[:2] == [
        'Error: kb mcp takes no arguments, but got "extra".',
        "Run kb mcp --help for the flags.",
    ]


def test_recorded_type_table_uses_the_display_title_and_actor(tmp_path):
    root = knowledge_base(tmp_path / "kb", {"": [CODEBASE]})
    path = root / "README.md"

    write(
        root,
        ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml",
        document_types_file("README.md", design_proposal()),
    )
    done = live(tmp_path / "home", "type", str(path))
    assert done.returncode == 0, done.stderr
    [row] = [line.split("\t") for line in done.stdout.splitlines()]
    assert row[:3] == ["design-proposal", CODEBASE, "record"]
    assert row[3] != "<unset>" and row[4] != "design-proposal"


@pytest.mark.parametrize(
    ("args", "suggestion", "help_line"),
    [
        (["setpu"], "setup", "Run kb --help for the commands."),
        (["--verison"], "--version", "Run kb --help for the commands."),
        (
            ["setup", "--remov", "codex"],
            "--remove",
            "Run kb setup --help for the flags.",
        ),
        (["setup", "codxe"], "codex", "Run kb setup --help for the flags."),
    ],
)
def test_typos_suggest_before_help_without_changing_settings(
    tmp_path, args, suggestion, help_line
):
    home = fixture_home(tmp_path)
    before = snapshot(home)
    done = live(home, *args)
    assert done.returncode == 2 and done.stdout == ""
    lines = done.stderr.splitlines()
    assert lines[0].startswith("Error: ")
    assert lines[1:] == [f"Did you mean {suggestion}?", help_line]
    assert snapshot(home) == before


def test_shared_link_feedback_names_multiple_harnesses(tmp_path):
    home = fixture_home(tmp_path)
    for harness in ["codex", "pi", "opencode"]:
        assert live(home, "setup", harness).returncode == 0
    done = live(home, "setup", "--remove", "codex")
    assert done.returncode == 0 and done.stdout == ""
    assert "Kept 9 skill links also used by Pi and OpenCode." in done.stderr
    done = live(home, "setup", "--remove", "pi")
    assert "Kept 9 skill links also used by OpenCode." in done.stderr
