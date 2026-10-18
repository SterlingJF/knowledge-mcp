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

from tests.harness import MODULE, server_parameters, session, texts

CLAUDE = json.loads((MODULE / ".claude-plugin" / "plugin.json").read_text())
CODEX = json.loads((MODULE / ".codex-plugin" / "plugin.json").read_text())
CODEX_SERVERS = json.loads((MODULE / "codex-mcp.json").read_text())
PROJECT = tomllib.loads((MODULE / "pyproject.toml").read_text())["project"]

CODEX_KEEPS = ("HOME", "PATH", "USER", "TMPDIR")


def uv_locations() -> dict[str, str]:
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
    # Explicit uv paths preserve cache access under a temporary HOME.
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


def test_every_description_copy_is_the_package_description():
    marketplace = json.loads(
        (MODULE.parent / ".claude-plugin/marketplace.json").read_text()
    )
    copies = [
        CLAUDE["description"],
        CODEX["description"],
        CODEX["interface"]["shortDescription"],
        CODEX["interface"]["longDescription"],
        marketplace["metadata"]["description"],
        marketplace["plugins"][0]["description"],
        (MODULE.parent / "README.md").read_text().splitlines()[2],
    ]
    assert (
        PROJECT["description"]
        == "Plain, structured thinking while you work. It's free, open, and local-first."
    )
    assert all(text == PROJECT["description"] for text in copies)


def test_both_manifests_expose_the_import_skill(tmp_path):
    plugin = copy_plugin(tmp_path)
    for manifest in (CLAUDE, CODEX):
        for folder in (MODULE, plugin):
            skill = folder / manifest["skills"] / "kb-import-document"
            assert skill_name(skill) == "kb-import-document"


def test_plugin_skill_names_are_unique_and_match_upstream():
    skills = sorted(path.parent.name for path in (MODULE / "skills").glob("*/SKILL.md"))
    upstream = (MODULE / "knowledge-bus" / "UPSTREAM.md").read_text()
    copied = [name for name in skills if name not in OWN_SKILLS]

    assert len(skills) == len(set(skills))
    for name in copied:
        assert f"| `skills/{name}/` " in upstream
    assert "kb-check" in copied and "kb-explore" in copied
    for name in OWN_SKILLS:
        assert f"| `skills/{name}/` " not in upstream


OWN_SKILLS = {"kb-import-document", "kb-track-document-types", "kb-write-document"}


def skill_name(folder: Path) -> str:
    front = (folder / "SKILL.md").read_text().split("---\n")[1]
    [line] = [line for line in front.splitlines() if line.startswith("name:")]
    return line.removeprefix("name:").strip()


def test_own_skills_are_preserved_in_copied_plugin(tmp_path):
    skills = MODULE / "skills"
    for manifest in (CLAUDE, CODEX):
        assert (MODULE / manifest["skills"]).resolve() == skills
    own = sorted(path.name for path in skills.iterdir() if path.name in OWN_SKILLS)
    assert own == sorted(OWN_SKILLS)

    plugin = copy_plugin(tmp_path)

    for name in own:
        copied = plugin / CODEX["skills"] / name / "SKILL.md"
        assert copied.read_bytes() == (skills / name / "SKILL.md").read_bytes()


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        (
            "kb-write-document",
            {
                "kb_get_document_type",
                "kbp_card",
                "kb_list_audiences",
                "kb_record_edit",
                "kb_list_edits",
            },
        ),
        (
            "kb-track-document-types",
            {"kb_prepare_document_types", "kb_get_document_type"},
        ),
        (
            "kb-import-document",
            {
                "kb_prepare_import",
                "kb_get_document_type",
                "kbp_card",
            },
        ),
    ],
)
def test_own_skills_reference_required_and_registered_tools(tmp_path, skill, expected):
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
