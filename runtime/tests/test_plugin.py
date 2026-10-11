"""Standalone plugin installation and server startup from Claude Code and Codex manifests."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
from mcp.client.stdio import StdioServerParameters

from tests.hosts import MODULE, server_parameters, session, texts

CLAUDE = json.loads((MODULE / ".claude-plugin" / "plugin.json").read_text())
CODEX = json.loads((MODULE / ".codex-plugin" / "plugin.json").read_text())
CODEX_SERVERS = json.loads((MODULE / "codex-mcp.json").read_text())
PROJECT = tomllib.loads((MODULE / "pyproject.toml").read_text())["project"]

# Baseline environment variables retained in the simulated Codex startup.
CODEX_KEEPS = ("HOME", "PATH", "USER", "TMPDIR")


def uv_locations() -> dict[str, str]:
    """Return uv cache and Python installation directories for subprocess reuse."""
    found = {}
    for name, command in (
        ("UV_CACHE_DIR", "cache"),
        ("UV_PYTHON_INSTALL_DIR", "python"),
    ):
        done = subprocess.run(
            ["uv", command, "dir"], capture_output=True, text=True, check=True
        )
        found[name] = done.stdout.strip()
    return found


def copy_plugin(tmp_path: Path) -> Path:
    """Copy the plugin directory to simulate installation outside the repository."""
    target = tmp_path / "installed" / "knowledge-mcp"
    shutil.copytree(
        MODULE,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".venv"),
    )
    return target


def version_answer(parameters: StdioServerParameters) -> str:
    async def steps(client):
        result = await client.call_tool("kbp_version", {})
        assert not result.is_error, texts(result)
        return texts(result)[0]

    return session(parameters, steps)


def test_codex_starts_the_server_from_a_copy_of_the_folder(tmp_path):
    plugin = copy_plugin(tmp_path)
    server = CODEX_SERVERS["mcpServers"]["knowledge-mcp"]
    assert server["cwd"] == "."
    home = tmp_path / "home"
    home.mkdir()
    env = {name: os.environ[name] for name in CODEX_KEEPS if name in os.environ}
    # A temporary HOME contains test logs; uv reuses its existing cache and Python installations.
    env |= {"HOME": str(home), **uv_locations()}

    answer = version_answer(
        StdioServerParameters(
            command=server["command"],
            args=server["args"],
            cwd=plugin / server["cwd"],
            env=env,
        )
    )

    assert answer.startswith("Knowledge Bus ")
    assert (home / ".local" / "state" / "knowledge-mcp" / "log.jsonl").is_file()
    assert list((home / ".cache" / "knowledge-mcp" / "environments").iterdir())


def test_codex_manifest_lists_state_directory_env_vars():
    # Codex forwards state-directory variables listed in env_vars.
    server = CODEX_SERVERS["mcpServers"]["knowledge-mcp"]
    assert server["env_vars"] == ["KNOWLEDGE_MCP_STATE_DIR", "XDG_STATE_HOME"]


def test_claude_manifest_starts_copied_plugin_from_other_cwd(tmp_path):
    plugin = copy_plugin(tmp_path)
    server = CLAUDE["mcpServers"]["knowledge-mcp"]
    elsewhere = tmp_path / "some-project"
    elsewhere.mkdir()
    root = str(plugin)

    answer = version_answer(
        StdioServerParameters(
            command=server["command"],
            args=[arg.replace("${CLAUDE_PLUGIN_ROOT}", root) for arg in server["args"]],
            cwd=elsewhere,
            env={
                "CLAUDE_PLUGIN_ROOT": root,
                "XDG_STATE_HOME": str(tmp_path / "state"),
                "XDG_CACHE_HOME": str(tmp_path / "cache"),
            },
        )
    )

    assert answer.startswith("Knowledge Bus ")


def test_corrupt_lock_hashes_fail_startup(tmp_path):
    plugin = copy_plugin(tmp_path)
    lock = plugin / "requirements.lock"
    text = lock.read_text()
    first = text.index("--hash=sha256:") + len("--hash=sha256:")
    lock.write_text(text[:first] + "0" * 64 + text[first + 64 :])
    second = lock.read_text().index("--hash=sha256:", first) + len("--hash=sha256:")
    text = lock.read_text()
    lock.write_text(text[:second] + "1" * 64 + text[second + 64 :])
    server = CODEX_SERVERS["mcpServers"]["knowledge-mcp"]
    env = {
        **{name: os.environ[name] for name in CODEX_KEEPS if name in os.environ},
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        **uv_locations(),
    }

    done = subprocess.run(
        [server["command"], *server["args"]],
        cwd=plugin,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    assert done.returncode != 0
    assert "hash" in done.stderr.lower()
    assert done.stdout == ""
    assert not any(
        (tmp_path / "cache" / "knowledge-mcp" / "environments").glob("[!.]*")
    )


def test_development_server_returns_knowledge_bus_version(tmp_path):
    assert version_answer(server_parameters(tmp_path)).startswith("Knowledge Bus ")


def test_both_manifests_name_the_same_plugin_and_skills():
    for manifest in (CLAUDE, CODEX):
        assert manifest["name"] == "knowledge-mcp"
        assert manifest["version"] == PROJECT["version"]
        assert manifest["skills"] == "./skills/"
    assert CODEX["mcpServers"] == "./codex-mcp.json"
    assert not (MODULE / ".mcp.json").exists()


def test_both_manifests_describe_the_checks_and_the_records():
    assert CLAUDE["description"] == CODEX["description"]
    for text in (CLAUDE["description"], CODEX["interface"]["longDescription"]):
        assert "before writing" in text
        assert "record of each edit" in text
        assert "each file's fit" in text
        assert "bring in documents written elsewhere" in text


def test_both_manifests_expose_the_bring_in_skill(tmp_path):
    plugin = copy_plugin(tmp_path)
    for manifest in (CLAUDE, CODEX):
        for folder in (MODULE, plugin):
            skill = folder / manifest["skills"] / "km-bring-in"
            assert skill_name(skill) == "km-bring-in"


def test_plugin_skill_names_are_unique_and_match_upstream():
    skills = sorted(path.parent.name for path in (MODULE / "skills").glob("*/SKILL.md"))
    upstream = (MODULE / "knowledge-bus" / "UPSTREAM.md").read_text()
    copied = [name for name in skills if not name.startswith("km-")]

    assert len(skills) == len(set(skills))
    for name in copied:
        assert f"| `skills/{name}/` " in upstream
    assert "kb-check" in copied and "kb-explore" in copied
    assert "| `skills/km-" not in upstream


def skill_name(folder: Path) -> str:
    front = (folder / "SKILL.md").read_text().split("---\n")[1]
    [line] = [line for line in front.splitlines() if line.startswith("name:")]
    return line.removeprefix("name:").strip()


def test_km_skills_are_preserved_in_copied_plugin(tmp_path):
    skills = MODULE / "skills"
    for manifest in (CLAUDE, CODEX):
        assert (MODULE / manifest["skills"]).resolve() == skills
    own = sorted(path.name for path in skills.glob("km-*"))
    assert own == ["km-bring-in", "km-fit-record", "km-write"]

    plugin = copy_plugin(tmp_path)

    for name in own:
        copied = plugin / CODEX["skills"] / name / "SKILL.md"
        assert copied.read_bytes() == (skills / name / "SKILL.md").read_bytes()


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        (
            "km-write",
            {"kb_fit", "kbp_card", "kb_audience", "kb_record_edit", "kb_edits"},
        ),
        ("km-fit-record", {"kb_fit_record", "kb_fit"}),
        (
            "km-bring-in",
            {"kb_mark", "kb_fit", "kbp_card", "kb_record_edit", "kb_edits"},
        ),
    ],
)
def test_km_skills_reference_required_and_registered_tools(tmp_path, skill, expected):
    text = (MODULE / "skills" / skill / "SKILL.md").read_text()

    async def steps(client):
        return {tool.name for tool in (await client.list_tools()).tools}

    tools = session(server_parameters(tmp_path), steps)
    named = set(re.findall(r"`(kb(?:p)?_[a-z_]+)`", text))
    assert expected <= named
    assert named <= tools
    assert skill_name(MODULE / "skills" / skill) == skill


def test_marketplaces_reference_local_plugin_directory():
    repo = MODULE.parent
    if not (repo / ".claude-plugin" / "marketplace.json").is_file():
        pytest.skip("Claude marketplace.json is absent beside the plugin directory.")
    claude = json.loads((repo / ".claude-plugin" / "marketplace.json").read_text())
    codex = json.loads((repo / ".agents" / "plugins" / "marketplace.json").read_text())

    assert claude["name"] == codex["name"] == "knowledge-mcp"
    [claude_entry] = claude["plugins"]
    [codex_entry] = codex["plugins"]
    assert claude_entry == {
        **claude_entry,
        "name": "knowledge-mcp",
        "source": "./runtime",
    }
    assert codex_entry["name"] == "knowledge-mcp"
    assert codex_entry["source"] == {"source": "local", "path": "./runtime"}
    assert {"policy", "category"} <= codex_entry.keys()
    assert (repo / claude_entry["source"]).resolve() == MODULE
