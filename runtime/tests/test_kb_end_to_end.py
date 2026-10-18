from __future__ import annotations

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters

from knowledge_mcp import bundled, configedit, version
from knowledge_mcp.configedit import json_value
from knowledge_mcp.harnesses import HARNESSES as HARNESS_SPECS
from knowledge_mcp.harnesses import Env
from tests.harness import (
    CODEBASE,
    MODULE,
    PRODUCT,
    candidates,
    fit,
    knowledge_base,
    listed,
    scope_arguments,
    session,
    type_arguments,
    write,
)

# Use a stable registration path without invoking the installed executable.
KB = "/opt/homebrew/bin/kb"
HARNESSES = ["claude-code", "codex", "claude-desktop", "pi", "opencode"]
SKILLS = [skill.name for skill in bundled.skills()]
DESKTOP = "Library/Application Support/Claude/claude_desktop_config.json"

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURES = {
    ".claude.json": (FIXTURE_DIR / "claude-code-initial-github-server.json")
    .read_bytes()
    .decode("utf-8"),
    ".codex/config.toml": (FIXTURE_DIR / "codex-initial-docs-server.toml")
    .read_bytes()
    .decode("utf-8"),
    DESKTOP: (FIXTURE_DIR / "claude-desktop-initial-filesystem-server.json")
    .read_bytes()
    .decode("utf-8"),
    ".pi/agent/mcp.json": (FIXTURE_DIR / "pi-initial-remote-jira-server.json")
    .read_bytes()
    .decode("utf-8"),
    ".config/opencode/opencode.json": (
        (FIXTURE_DIR / "opencode-initial-remote-search-server.jsonc")
        .read_bytes()
        .decode("utf-8")
    ),
}


def snapshot(home: Path) -> dict[str, object]:
    """Removal must restore file bytes, permissions and symlink targets."""
    found: dict[str, object] = {}
    for path in sorted(home.rglob("*")):
        relative = str(path.relative_to(home))
        if path.is_symlink():
            found[relative] = ("link", os.readlink(path))
        elif path.is_dir():
            found[relative] = ("folder", stat.S_IMODE(path.stat().st_mode))
        else:
            found[relative] = (
                "file",
                path.read_bytes(),
                stat.S_IMODE(path.stat().st_mode),
            )
    return found


def fixture_home(root: Path) -> Path:
    home = root / "home"
    for relative, text in FIXTURES.items():
        write(home, relative, text)
    return home


def kb(
    home: Path, *args: str, path: str = "", check: bool = True, **env: str
) -> subprocess.CompletedProcess[str]:
    """Start kb with an isolated environment and the supplied PATH."""
    done = subprocess.run(
        [sys.executable, "-m", "knowledge_mcp.cli", *args],
        cwd=MODULE,
        env={
            "HOME": str(home),
            "PATH": path,
            "KNOWLEDGE_MCP_COMMAND": KB,
            "PYTHONIOENCODING": "utf-8",
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if check:
        assert done.returncode == 0, done.stderr + done.stdout
    return done


def entry(home: Path, harness: str) -> object:
    if harness == "codex":
        config = tomllib.loads((home / ".codex/config.toml").read_text())
        return config.get("mcp_servers", {}).get("knowledge-mcp")
    file = {
        "claude-code": ".claude.json",
        "claude-desktop": DESKTOP,
        "pi": ".pi/agent/mcp.json",
        "opencode": ".config/opencode/opencode.json",
    }[harness]

    data = json_value((home / file).read_text())
    return data.get("mcp" if harness == "opencode" else "mcpServers", {}).get(
        "knowledge-mcp"
    )


# Keep harness CLI calls local so setup tests can simulate removal failures.
CLI_STUB = """#!{python}
import os, sys
from pathlib import Path

from knowledge_mcp import configedit
from knowledge_mcp.harnesses import HARNESSES, Env

name = Path(sys.argv[0]).name
with open(os.environ["STUB_LOG"], "a") as log:
    log.write(" ".join([name, *sys.argv[1:]]) + "\\n")
harness = HARNESSES[{{"claude": "claude-code"}}.get(name, name)]
path = harness.config(Env.current())
text = path.read_text() if path.exists() else ""
if sys.argv[2] == "add":
    command = sys.argv[sys.argv.index("--") + 1 :]
    insert = configedit.toml_insert if harness.format == "toml" else configedit.json_insert
    where = harness.path[0] if harness.format == "toml" else harness.path
    text, piece = insert(text, where, "knowledge-mcp", harness.entry(command))
    Path(os.environ["STUB_LOG"] + "." + harness.id).write_text(piece)
else:
    if os.environ.get("STUB_FAIL"):
        sys.exit("no server named knowledge-mcp")
    remove = configedit.toml_remove if harness.format == "toml" else configedit.json_remove
    where = harness.path[0] if harness.format == "toml" else harness.path
    text = remove(text, where, "knowledge-mcp", Path(os.environ["STUB_LOG"] + "." + harness.id).read_text())
path.write_text(text)
"""


def harness_clis(root: Path) -> tuple[Path, Path]:
    folder = root / "bin"
    folder.mkdir()
    for name in ("claude", "codex", "pi"):
        stub = folder / name
        stub.write_text(CLI_STUB.format(python=sys.executable))
        stub.chmod(0o755)
    return folder, root / "cli.log"


def cli_remove(home: Path, harness: str, log: Path) -> None:
    """Simulate manual removal without updating the setup record."""

    spec = HARNESS_SPECS[harness]
    path = spec.config(Env(home, {"HOME": str(home)}))
    text = path.read_text()
    piece = Path(f"{log}.{harness}").read_text()
    if spec.format == "toml":
        text = configedit.toml_remove(text, spec.path[0], "knowledge-mcp", piece)
    else:
        text = configedit.json_remove(text, spec.path, "knowledge-mcp", piece)
    path.write_text(text)


EXPECTED = {
    "claude-code": {"type": "stdio", "command": KB, "args": ["mcp"]},
    "codex": {
        "command": KB,
        "args": ["mcp"],
        "env_vars": ["KNOWLEDGE_MCP_STATE_DIR", "XDG_STATE_HOME"],
    },
    "claude-desktop": {"command": KB, "args": ["mcp"]},
    "pi": {"command": KB, "args": ["mcp"]},
    "opencode": {"type": "local", "command": [KB, "mcp"], "enabled": True},
}
SKILL_FOLDER = {
    "claude-code": ".claude/skills",
    "codex": ".agents/skills",
    "pi": ".agents/skills",
    "opencode": ".agents/skills",
}


def assert_mismatched_command(problem, missing, stable):
    actual = shlex.join([str(missing), "mcp"])
    expected = shlex.join([str(stable), "mcp"])
    assert problem.count(actual) == 1
    assert problem.count(expected) == 1
    assert problem.index(actual) < problem.index(expected)


class TestSetup:
    @pytest.mark.parametrize("harness", HARNESSES)
    def test_setup_registers_harness_and_remove_restores_home(self, tmp_path, harness):
        home = fixture_home(tmp_path)
        before = snapshot(home)

        done = kb(home, "setup", harness)

        assert entry(home, harness) == EXPECTED[harness]
        assert done.stdout == ""
        lines = done.stderr.splitlines()
        assert lines[0].startswith("Registered knowledge-mcp with ")
        assert str(home) in lines[0]
        [backup] = (home / ".local/state/knowledge-mcp/setup/backups").iterdir()
        assert f"backup at {backup}." in lines[0]
        assert "\x1b[" not in done.stderr
        steps = lines[1:]
        if harness in SKILL_FOLDER:
            folder = home / SKILL_FOLDER[harness]
            for name in SKILLS:
                link = folder / name
                assert link.is_symlink()
                assert Path(os.readlink(link)) == bundled.SKILLS / name
                assert (link / "SKILL.md").is_file()
        else:
            assert not (home / ".claude/skills").exists()
            assert not (home / ".agents/skills").exists()
            state_file = home / ".local/state/knowledge-mcp/setup/state.json"
            record = json.loads(state_file.read_text())["hosts"][harness]
            assert record["links"] == []

            skills_path = str(MODULE / "skills")
            [guidance] = [
                line for line in done.stderr.splitlines() if skills_path in line
            ]
            assert "Claude desktop app" in done.stderr
            assert any(line.startswith("mkdir -p ") for line in steps)
            [upload] = [line for line in steps if line.strip().startswith("Upload ")]
            assert "ZIP" in upload
            assert "Customize → Skills" in upload
            assert "(cd " in guidance
            assert not guidance.startswith(("warning: ", "problem: "))

        assert not any(
            line.startswith(("warning: ", "problem: "))
            for line in done.stdout.splitlines()
        )

        kb(home, "setup", "--remove", harness)

        assert snapshot(home) == before
        if harness == "codex":
            executable = tmp_path / "tool folder" / "kb"
            spaced = kb(home, "setup", harness, KNOWLEDGE_MCP_COMMAND=str(executable))
            assert entry(home, harness)["command"] == str(executable)
            assert entry(home, harness)["args"] == ["mcp"]
            assert spaced.stdout == ""
            kb(home, "setup", "--remove", harness)
            assert snapshot(home) == before

    def test_remove_preserves_shared_links_until_last_harness(self, tmp_path):
        home = fixture_home(tmp_path)
        before = snapshot(home)
        for harness in HARNESSES:
            kb(home, "setup", harness)
        for harness in HARNESSES:
            assert entry(home, harness) == EXPECTED[harness]

        for harness in ["pi", "claude-code", "opencode", "claude-desktop"]:
            kb(home, "setup", "--remove", harness)
            assert (home / ".agents/skills/kb-check").is_symlink()
        kb(home, "setup", "--remove", "codex")

        assert snapshot(home) == before

    def test_remove_restores_home_without_preexisting_settings(self, tmp_path):
        home = tmp_path / "home"
        # Removal must preserve settings folders that existed before setup.
        (home / "Library/Application Support/Claude").mkdir(parents=True)
        before = snapshot(home)
        for harness in HARNESSES:
            kb(home, "setup", harness)
        assert (home / ".codex/config.toml").is_file()
        assert (home / ".local/state/knowledge-mcp/setup/state.json").is_file()

        for harness in reversed(HARNESSES):
            done = kb(home, "setup", "--remove", harness)

        assert "rm -r" not in done.stdout
        assert snapshot(home) == before

    @pytest.mark.parametrize("state", ["home", "xdg", "variable"])
    def test_last_harness_remove_reports_state_dir_and_preserves_log(
        self, tmp_path, state
    ):
        home = fixture_home(tmp_path)
        # Create the state parent before setup so removal preserves the existing directory.
        base = {
            "home": home / ".local/state",
            "xdg": tmp_path / "my state",
            "variable": tmp_path / "my state",
        }[state]
        base.mkdir(parents=True)
        history = base / ("my history" if state == "variable" else "knowledge-mcp")
        env = {
            "home": {},
            "xdg": {"XDG_STATE_HOME": str(base)},
            "variable": {
                "KNOWLEDGE_MCP_STATE_DIR": str(history),
                "XDG_STATE_HOME": str(tmp_path / "other"),
            },
        }[state]
        before = snapshot(home)
        kb(home, "setup", "codex", **env)
        kb(home, "setup", "pi", **env)
        rfc = write(
            knowledge_base(tmp_path / "codebase", {"": [CODEBASE]}),
            "docs/rfcs/0042-cache.md",
            "# Cache\n",
        )
        kb(home, "type", str(rfc), **env)
        kb(home, "setup", "--remove", "codex", **env)

        done = kb(home, "setup", "--remove", "pi", **env)

        assert done.stdout == ""
        lines = done.stderr.splitlines()
        named = env.get("KNOWLEDGE_MCP_STATE_DIR", "<unset>")
        assert lines[-2:] == [
            f"KNOWLEDGE_MCP_STATE_DIR: {named}",
            f"log.jsonl, edits.jsonl and the explorer folder stay in {history}.",
        ]
        assert "rm -r" not in done.stdout
        assert sorted(path.name for path in history.iterdir()) == ["log.jsonl"]
        after = snapshot(home)
        kept = str((home / ".local/state/knowledge-mcp").relative_to(home))
        assert {
            name: value
            for name, value in after.items()
            if name != kept and not name.startswith(kept + "/")
        } == before
        assert not (tmp_path / "other").exists()

    def test_remove_omits_state_report_while_other_harnesses_remain(self, tmp_path):
        home = fixture_home(tmp_path)
        history = home / ".local/state/knowledge-mcp"
        kb(home, "setup", "codex")
        kb(home, "setup", "claude-desktop")
        rfc = write(tmp_path / "codebase", "docs/rfcs/0042-cache.md", "# Cache\n")
        kb(home, "type", str(rfc))
        assert (history / "log.jsonl").is_file()

        done = kb(home, "setup", "--remove", "codex")

        assert str(history) not in done.stdout
        assert "rm -r" not in done.stdout
        kb(home, "setup", "--remove", "claude-desktop")

    def test_remove_preserves_user_config_changes(self, tmp_path):
        home = fixture_home(tmp_path)
        kb(home, "setup", "codex")
        kb(home, "setup", "claude-desktop")
        config = home / ".codex/config.toml"
        config.write_text(
            config.read_text().replace('model = "gpt-5"', 'model = "gpt-5.5"')
        )
        desktop = home / DESKTOP
        desktop.write_text(
            desktop.read_text().replace(
                '"globalShortcut": ""', '"globalShortcut": "Cmd+K"'
            )
        )

        kb(home, "setup", "--remove", "codex")
        kb(home, "setup", "--remove", "claude-desktop")

        assert config.read_text() == FIXTURES[".codex/config.toml"].replace(
            'model = "gpt-5"', 'model = "gpt-5.5"'
        )
        assert desktop.read_text() == FIXTURES[DESKTOP].replace(
            '"globalShortcut": ""', '"globalShortcut": "Cmd+K"'
        )

    def test_a_backup_exists_until_removal(self, tmp_path):
        home = fixture_home(tmp_path)
        done = kb(home, "setup", "pi")
        [backup] = (home / ".local/state/knowledge-mcp/setup/backups").iterdir()
        assert backup.read_text() == FIXTURES[".pi/agent/mcp.json"]
        assert str(backup) in done.stderr

        kb(home, "setup", "--remove", "pi")

        assert not backup.exists()

    def test_setup_rejects_conflicting_entry_without_changes(self, tmp_path):
        home = fixture_home(tmp_path)
        desktop = home / DESKTOP
        desktop.write_text(
            '{"mcpServers": {"knowledge-mcp": {"command": "uv", "args": ["run"]}}}\n'
        )
        before = snapshot(home)

        done = kb(home, "setup", "claude-desktop", check=False)

        assert done.returncode == 1
        assert "already has a knowledge-mcp entry" in done.stderr
        assert snapshot(home) == before

    def test_setup_uses_harness_clis_except_for_codex_config(self, tmp_path):
        home = fixture_home(tmp_path)
        bin_folder, log = harness_clis(tmp_path)
        before = snapshot(home)

        for harness in ("claude-code", "codex", "pi"):
            kb(home, "setup", harness, path=str(bin_folder), STUB_LOG=str(log))
            assert entry(home, harness) == EXPECTED[harness]
        for harness in ("claude-code", "codex", "pi"):
            kb(
                home,
                "setup",
                "--remove",
                harness,
                path=str(bin_folder),
                STUB_LOG=str(log),
            )

        assert log.read_text().splitlines() == [
            f"claude mcp add --scope user knowledge-mcp -- {KB} mcp",
            f"pi mcp add knowledge-mcp -- {KB} mcp",
            "claude mcp remove --scope user knowledge-mcp",
            "pi mcp remove knowledge-mcp",
        ]
        assert snapshot(home) == before

    @pytest.mark.parametrize("harness", ["claude-code", "pi"])
    def test_remove_skips_harness_cli_for_deleted_entry(self, tmp_path, harness):
        home = fixture_home(tmp_path)
        bin_folder, log = harness_clis(tmp_path)
        before = snapshot(home)
        kb(home, "setup", harness, path=str(bin_folder), STUB_LOG=str(log))
        cli_remove(home, harness, log)

        done = kb(
            home,
            "setup",
            "--remove",
            harness,
            path=str(bin_folder),
            STUB_LOG=str(log),
            STUB_FAIL="1",
        )

        assert "Removed the setup record for " in done.stderr
        assert len(log.read_text().splitlines()) == 1
        assert snapshot(home) == before
        kb(home, "setup", harness, path=str(bin_folder), STUB_LOG=str(log))

    def test_remove_cleans_up_without_harness_cli_or_entry(self, tmp_path):
        home = fixture_home(tmp_path)
        bin_folder, log = harness_clis(tmp_path)
        before = snapshot(home)
        kb(home, "setup", "pi", path=str(bin_folder), STUB_LOG=str(log))
        cli_remove(home, "pi", log)

        kb(home, "setup", "--remove", "pi")

        assert snapshot(home) == before

    def test_remove_recovers_from_cli_failure_after_entry_deletion(self, tmp_path):
        home = fixture_home(tmp_path)
        bin_folder, log = harness_clis(tmp_path)
        before = snapshot(home)
        kb(home, "setup", "pi", path=str(bin_folder), STUB_LOG=str(log))
        config = home / ".pi/agent/mcp.json"
        registered_bytes = config.read_bytes()
        state_file = home / ".local/state/knowledge-mcp/setup/state.json"
        registered_record = json.loads(state_file.read_text())["hosts"]["pi"]

        failed = kb(
            home,
            "setup",
            "--remove",
            "pi",
            path=str(bin_folder),
            STUB_LOG=str(log),
            STUB_FAIL="1",
            check=False,
        )

        assert failed.returncode == 1
        assert failed.stdout == ""
        assert entry(home, "pi") == EXPECTED["pi"]
        assert config.read_bytes() == registered_bytes
        assert not any((home / ".agents/skills").iterdir())

        pending = json.loads(state_file.read_text())["hosts"]["pi"]
        assert pending == {**registered_record, "links": []}
        assert pending["method"] == "cli"
        assert pending["config"] == str(config)
        assert pending["cli"] == "pi"

        [problem] = [
            line for line in failed.stderr.splitlines() if line.startswith("Error: ")
        ]
        assert str(config) in failed.stderr
        assert "no server named knowledge-mcp" in problem
        assert "pi mcp remove knowledge-mcp" in problem
        assert "kb setup --remove pi" in failed.stderr
        assert "`" not in failed.stderr
        assert log.read_text().splitlines()[-1] == "pi mcp remove knowledge-mcp"
        cli_remove(home, "pi", log)
        kb(home, "setup", "--remove", "pi")
        assert snapshot(home) == before

    def test_setup_warns_on_duplicates_and_preserves_existing_skills(self, tmp_path):
        home = fixture_home(tmp_path)
        write(
            home,
            ".claude/plugins/installed_plugins.json",
            json.dumps({"version": 2, "plugins": {"knowledge-bus@knowledge-bus": []}}),
        )
        config = home / ".codex/config.toml"
        config.write_text(
            config.read_text()
            + (FIXTURE_DIR / "enabled-knowledge-mcp-plugin.toml")
            .read_bytes()
            .decode("utf-8")
        )
        write(
            home,
            ".pi/agent/settings.json",
            json.dumps({"packages": ["npm:@knowledge-bus/pi"]}, indent=2) + "\n",
        )
        opencode_config = home / ".config/opencode/opencode.json"
        opencode_config.write_text(
            opencode_config.read_text().replace(
                '"theme": "system",',
                '"theme": "system",\n  "plugin": ["@knowledge-bus/opencode@latest"],',
            )
        )
        write(
            home,
            ".agents/skills/kb-check/SKILL.md",
            (FIXTURE_DIR / "copied-kb-check-skill.md").read_bytes().decode("utf-8"),
        )
        before = snapshot(home)

        claude = kb(home, "setup", "claude-code")
        codex = kb(home, "setup", "codex")
        kept = home / ".agents/skills/kb-check"
        assert (
            len(
                [
                    line
                    for line in codex.stderr.splitlines()
                    if line.startswith("Warning: ") and str(kept) in line
                ]
            )
            == 1
        )
        assert not kept.is_symlink()
        after_setup = snapshot(home)
        assert (
            after_setup[".agents/skills/kb-check"] == before[".agents/skills/kb-check"]
        )
        assert (
            after_setup[".agents/skills/kb-check/SKILL.md"]
            == before[".agents/skills/kb-check/SKILL.md"]
        )
        pi = kb(home, "setup", "pi")
        opencode = kb(home, "setup", "opencode")

        assert "and Claude Code plugin knowledge-bus@knowledge-bus," in claude.stderr
        assert "and Codex plugin knowledge-mcp@knowledge-mcp," in codex.stderr
        assert "and Pi package npm:@knowledge-bus/pi," in pi.stderr
        assert "and OpenCode plugin @knowledge-bus/opencode@latest," in opencode.stderr

        for harness in ("opencode", "codex", "pi", "claude-code"):
            kb(home, "setup", "--remove", harness)
        assert snapshot(home) == before

    def test_opencode_setup_warns_about_claude_skill_links(self, tmp_path):
        home = fixture_home(tmp_path)
        executable = str(Path(sys.executable).parent / "kb")
        kb(home, "setup", "claude-code", KNOWLEDGE_MCP_COMMAND=executable)

        done = kb(home, "setup", "opencode", KNOWLEDGE_MCP_COMMAND=executable)

        [warning] = [
            line
            for line in done.stderr.splitlines()
            if line.startswith("Warning:") and "also reads" in line
        ]
        assert (
            f"OpenCode also reads {home / '.claude/skills'}, where kb setup linked"
            in warning
        )
        before_check = snapshot(home)
        for mode in ((), ("--verbose",)):
            doctor = kb(
                home, "doctor", *mode, check=False, KNOWLEDGE_MCP_COMMAND=executable
            )
            assert doctor.returncode == 0
            assert "Warning: " in doctor.stderr
            assert "0 problems" in doctor.stdout
            assert "1 warning" in doctor.stdout
            [diagnostic] = [
                line
                for line in doctor.stderr.splitlines()
                if line.startswith("Warning: ")
            ]
            assert "OpenCode" in diagnostic
            assert str(home / ".claude/skills") in diagnostic
            assert all(name in diagnostic for name in SKILLS)
        assert snapshot(home) == before_check
        kb(home, "setup", "--remove", "opencode")
        kb(home, "setup", "--remove", "claude-code")

    def test_doctor_reports_missing_and_mismatched_harness_commands(self, tmp_path):
        home = fixture_home(tmp_path)
        missing = tmp_path / "missing kb"
        kb(home, "setup", "codex", KNOWLEDGE_MCP_COMMAND=str(missing))
        stable = tmp_path / "kb"
        stable.write_text("#!/bin/sh\n")

        report = kb(home, "doctor", check=False, KNOWLEDGE_MCP_COMMAND=str(stable))
        assert report.returncode == 1
        [problem] = [
            line
            for line in report.stderr.splitlines()
            if line.startswith("Error: Codex: ")
        ]
        assert "knowledge-mcp" in problem
        assert "1 problem" in report.stdout
        assert "Bundled skills\n" not in report.stdout

        assert_mismatched_command(problem, missing, stable)

        report = kb(home, "doctor", check=False, KNOWLEDGE_MCP_COMMAND=str(missing))
        assert f"Error: Codex: {missing} is missing." in report.stderr
        assert "1 problem" in report.stdout
        before_check = snapshot(home)
        report = kb(
            home, "doctor", "--verbose", check=False, KNOWLEDGE_MCP_COMMAND=str(missing)
        )
        assert report.returncode == 1
        assert f"Error: Codex: {missing} is missing." in report.stderr
        assert "knowledge-bus: 0.10.0" in report.stdout
        assert "Release: v0.10.0" in report.stdout
        assert "Claude Code: not registered" in report.stdout
        assert f"Codex skill links: {len(SKILLS)}" in report.stdout
        assert f"Codex skills folder: {home / '.agents/skills'}" in report.stdout
        assert "KNOWLEDGE_MCP_STATE_DIR: <unset>" in [
            line.strip() for line in report.stdout.splitlines()
        ]
        assert f"State directory: {home / '.local/state/knowledge-mcp'}" in [
            line.strip() for line in report.stdout.splitlines()
        ]

        assert snapshot(home) == before_check

        config = home / ".codex/config.toml"
        original = config.read_text()
        config.write_text(
            configedit.toml_remove(original, "mcp_servers", "knowledge-mcp", None)
        )
        drifted = snapshot(home)
        for mode in ((), ("--verbose",)):
            drift = kb(
                home, "doctor", *mode, check=False, KNOWLEDGE_MCP_COMMAND=str(stable)
            )
            assert drift.returncode == 1
            [problem] = [
                line
                for line in drift.stderr.splitlines()
                if line.startswith("Error: Codex:")
            ]
            assert str(config) in problem
            lines = [line.strip() for line in drift.stderr.splitlines()]
            for command in ("kb setup --remove codex", "kb setup codex"):
                assert any(command in line for line in lines)
                assert command not in problem
            assert "Run kb setup --remove codex, then kb setup codex." in drift.stderr
        assert snapshot(home) == drifted
        config.write_text("[mcp_servers\n")
        invalid = kb(home, "doctor", check=False, KNOWLEDGE_MCP_COMMAND=str(stable))
        assert invalid.returncode == 1
        assert str(config) in invalid.stderr
        assert f"kb can't read {config}: " in invalid.stderr
        config.write_text(original)
        kb(home, "setup", "--remove", "codex")

    def test_doctor_reports_state_dir_without_creating_directory(self, tmp_path):
        home = fixture_home(tmp_path)
        chosen = tmp_path / "my history"

        before_check = snapshot(home)
        report = kb(home, "doctor", check=False, KNOWLEDGE_MCP_STATE_DIR=str(chosen))

        assert report.returncode == 0
        assert "No problems found." in report.stdout
        assert sum("not registered" in line for line in report.stdout.splitlines()) == 5
        assert "Bundled spec files\n" not in report.stdout
        assert "Bundled skills\n" not in report.stdout
        assert str(chosen) not in report.stdout
        report = kb(
            home,
            "doctor",
            "--verbose",
            check=False,
            KNOWLEDGE_MCP_STATE_DIR=str(chosen),
        )
        assert report.returncode == 0
        assert "problem: " not in report.stdout
        for harness in ("Claude Code", "Codex", "Claude desktop app", "Pi", "OpenCode"):
            assert f"{harness}: not registered" in report.stdout
        assert report.stdout.index("Harnesses\n") < report.stdout.index(
            "Bundled spec files\n"
        )
        assert report.stdout.index("Bundled skills\n") < report.stdout.index("State\n")
        lines = [line.strip() for line in report.stdout.splitlines()]
        assert f"KNOWLEDGE_MCP_STATE_DIR: {chosen}" in lines
        assert f"State directory: {chosen}" in lines
        assert not chosen.exists()
        assert snapshot(home) == before_check


class TestCommands:
    def test_version_reports_kb_and_knowledge_bus_versions(self, tmp_path):
        done = kb(tmp_path, "--version")
        assert done.stderr == ""
        [kb_line, bus_line] = done.stdout.splitlines()

        try:
            expected_kb = metadata.version("knowledge-mcp")
        except metadata.PackageNotFoundError:
            expected_kb = tomllib.loads((MODULE / "pyproject.toml").read_text())[
                "project"
            ]["version"]
        expected_bus = metadata.version("knowledge-bus")

        assert kb_line == f"kb {expected_kb}"
        assert bus_line == f"knowledge-bus {expected_bus}"

    def test_kbp_preserves_cli_streams_and_exit_code(self, tmp_path):
        kbp = Path(sys.executable).parent / "kbp"
        for mode, args in (
            (["--version"], ["--version"]),
            (["card", "no-such-kind"], ["--card", "no-such-kind"]),
            (["kinds"], ["--kinds"]),
        ):
            direct = subprocess.run(
                [str(kbp), *args],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
            )
            through = subprocess.run(
                [sys.executable, "-m", "knowledge_mcp.cli", "kbp", *mode],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
            )
            assert (through.stdout, through.stderr, through.returncode) == (
                direct.stdout,
                direct.stderr,
                direct.returncode,
            )

    def test_type_answers_like_the_kb_get_document_type_tool(self, tmp_path):
        root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
        rfc = write(root, "docs/rfcs/0042-cache.md", "# Cache\n")

        done = kb(
            tmp_path,
            "type",
            "--json",
            str(rfc),
            "--role",
            "maintainer",
            XDG_STATE_HOME=str(tmp_path / "state"),
        )
        answer = json.loads(done.stdout)

        assert candidates(answer)[0] == (CODEBASE, "design-proposal")
        assert all(
            spec["source"] == bundled.label() for spec in answer["universe_specs"]
        )

        async def steps(client):
            return await client.call_tool(
                "kb_get_document_type",
                {
                    **type_arguments(
                        root, "docs/rfcs/0042-cache.md", role="maintainer"
                    ),
                    "listing": [{"path": "docs/rfcs/0042-cache.md"}],
                },
            )

        through_server = fit(session(kb_mcp(tmp_path / "state"), steps))
        assert answer == through_server

    def test_type_inherits_parent_universe_via_workspace_yaml(self, tmp_path):
        root = knowledge_base(tmp_path / "kb", {"": [PRODUCT], "team": []})
        write(
            root, "team/.knowledge-bus/workspace.yaml", f"from_parent:\n  - {PRODUCT}\n"
        )
        pricing = write(root, "team/docs/product/pricing.md", "# Pricing\n")

        answer = json.loads(
            kb(
                tmp_path,
                "type",
                "--json",
                str(pricing),
                "--role",
                "product lead",
                XDG_STATE_HOME=str(tmp_path / "state"),
            ).stdout
        )

        assert (PRODUCT, "design-doc") in listed(answer)
        assert [spec["id"] for spec in answer["universe_specs"]] == [PRODUCT]

    def test_type_uses_bundled_specs_without_definitions(self, tmp_path):
        folder = tmp_path / "plain"
        readme = write(folder, "README.md", "# Plain\n")
        quote = write(folder, "vendor-quote.md", "# Quote\n")

        readme_answer = json.loads(
            kb(
                tmp_path,
                "type",
                "--json",
                str(readme),
                XDG_STATE_HOME=str(tmp_path / "state"),
            ).stdout
        )
        quote_answer = json.loads(
            kb(
                tmp_path,
                "type",
                "--json",
                str(quote),
                XDG_STATE_HOME=str(tmp_path / "state"),
            ).stdout
        )

        assert any(kind == "readme" for _spec, kind in candidates(readme_answer))
        assert quote_answer["candidates"] == []

    def test_type_matches_rfc_folder_without_definitions(self, tmp_path):
        rfc = write(tmp_path / "repo", "docs/rfcs/0042-cache.md", "# Cache\n")
        (tmp_path / "repo" / ".git").mkdir()

        answer = json.loads(
            kb(
                tmp_path,
                "type",
                "--json",
                str(rfc),
                XDG_STATE_HOME=str(tmp_path / "state"),
            ).stdout
        )

        assert answer["location"] == str(rfc)
        assert {(CODEBASE, "design-proposal"), (PRODUCT, "design-doc")} <= set(
            candidates(answer)
        )

    def test_type_fails_for_missing_parent_directory(self, tmp_path):
        done = kb(tmp_path, "type", str(tmp_path / "missing" / "a.md"), check=False)
        assert done.returncode == 2
        assert "does not exist" in done.stderr
        assert "kb type --help" in done.stderr


def kb_mcp(state: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "knowledge_mcp.cli", "mcp"],
        cwd=MODULE,
        env={"XDG_STATE_HOME": str(state), "PATH": os.environ["PATH"]},
    )


THREAD = """\
# #cache-rollout, Tuesday

Ana: The evening build never finishes since the cache landed. We decided to drop the evening build and keep only the morning build.

Ben: Agreed. If build times double again we reopen the question.

Ana: Next up for the maintainers: ship the read cache behind a flag in 0.4, then the write cache in 0.5.
"""


def test_kb_mcp_initialize_returns_server_name(tmp_path):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "brew", "version": "1"},
        },
    }
    done = subprocess.run(
        [sys.executable, "-m", "knowledge_mcp.cli", "mcp"],
        input=json.dumps(request) + "\n",
        cwd=MODULE,
        env={"HOME": str(tmp_path), "PATH": ""},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert '"name":"knowledge-mcp"' in done.stdout


def test_kb_mcp_lists_tools_and_returns_fit_and_mark_results(tmp_path):
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, "docs/rfcs/0042-cache.md", "# Cache\n")

    async def steps(client):
        tools = {tool.name for tool in (await client.list_tools()).tools}
        fitted = await client.call_tool(
            "kb_get_document_type", type_arguments(root, "docs/rfcs/0042-cache.md")
        )
        marked = await client.call_tool(
            "kb_prepare_import",
            {
                "location": "pasted in chat",
                "text": THREAD,
                **scope_arguments(root, "docs/notes.md"),
            },
        )
        return tools, fitted, marked

    tools, fitted, marked = session(kb_mcp(tmp_path / "state"), steps)

    assert {
        "kb_get_document_type",
        "kb_prepare_document_types",
        "kb_list_audiences",
        "kb_record_edit",
        "kb_list_edits",
        "kb_prepare_import",
        "kbp_card",
        "kbp_kinds",
    } <= tools
    assert not any(name.startswith("km_") for name in tools)
    assert not fitted.is_error and not marked.is_error


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv")
def test_sdist_wheel_install_links_skills_via_opt_path(
    tmp_path,
):
    dist = tmp_path / "dist"
    uv = shutil.which("uv")
    subprocess.run(
        [uv, "build", "--sdist", "--out-dir", str(dist), str(MODULE)],
        check=True,
        capture_output=True,
    )
    [sdist] = dist.glob("knowledge_mcp-*.tar.gz")
    subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(dist), str(sdist)],
        check=True,
        capture_output=True,
    )
    [wheel] = dist.glob("knowledge_mcp-*.whl")
    venv = tmp_path / "libexec"
    subprocess.run(
        [uv, "venv", "--quiet", "--python", sys.executable, str(venv)], check=True
    )
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--quiet",
            "--python",
            str(venv / "bin/python"),
            "-r",
            str(MODULE / "requirements.lock"),
            str(wheel),
        ],
        check=True,
        capture_output=True,
    )
    kb_script = venv / "bin" / "kb"
    home = tmp_path / "home"
    home.mkdir()
    env = {"HOME": str(home), "PATH": ""}

    shown = subprocess.run(
        [str(kb_script), "--version"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    doctor = subprocess.run(
        [str(kb_script), "doctor"], env=env, capture_output=True, text=True, check=False
    )

    assert shown.stdout.splitlines() == [f"kb {version()}", "knowledge-bus 0.10.0"]
    assert doctor.returncode == 0, doctor.stdout + doctor.stderr
    assert "No problems found." in doctor.stdout
    assert "Bundled skills\n" not in doctor.stdout
    verbose = subprocess.run(
        [str(kb_script), "doctor", "--verbose"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verbose.returncode == doctor.returncode
    assert "Bundled skills\n" in verbose.stdout
    for name in SKILLS:
        assert f"    {name}" in verbose.stdout.splitlines()
    assert not (venv / "bin" / "knowledge-mcp").exists()
    # Retarget the opt symlink to simulate a Homebrew upgrade.
    [package] = venv.glob("lib/python*/site-packages/knowledge_mcp")
    opt = tmp_path / "opt" / "knowledge-mcp"
    opt.parent.mkdir()
    opt.symlink_to(package)
    env["KNOWLEDGE_MCP_DATA"] = str(opt)
    env["KNOWLEDGE_MCP_COMMAND"] = str(kb_script)
    subprocess.run(
        [str(kb_script), "setup", "codex"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    link = home / ".agents/skills/kb-check"
    assert Path(os.readlink(link)) == opt / "skills" / "kb-check"
    assert f'command = "{kb_script}"' in (home / ".codex/config.toml").read_text()

    upgraded = tmp_path / "upgraded"
    shutil.copytree(package, upgraded, symlinks=True)
    (upgraded / "skills/kb-check/SKILL.md").write_text("upgraded\n")
    opt.unlink()
    opt.symlink_to(upgraded)
    assert (link / "SKILL.md").read_text() == "upgraded\n"

    subprocess.run(
        [str(kb_script), "setup", "--remove", "codex"],
        env=env,
        check=True,
        capture_output=True,
    )
    assert sorted(path.name for path in home.iterdir()) == []
