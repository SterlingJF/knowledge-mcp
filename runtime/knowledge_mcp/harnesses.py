"""Settings file, server entry and skill folders for each supported harness."""

from __future__ import annotations

import os
import re
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from knowledge_mcp import configedit, log

NAME = "knowledge-mcp"
# Plugins and packages can duplicate tools or skills registered by kb setup.
DUPLICATE = re.compile(r"(^|[/@])knowledge-(bus|mcp)(/|@|$|-)")


@dataclass(frozen=True)
class Env:
    home: Path
    environ: dict[str, str]

    @classmethod
    def current(cls) -> Env:
        return cls(Path.home(), dict(os.environ))

    def named(self, variable: str, default: Path) -> Path:
        value = self.environ.get(variable, "")
        return (
            Path(value).expanduser()
            if os.path.isabs(os.path.expanduser(value))
            else default
        )


@dataclass(frozen=True)
class Harness:
    id: str
    title: str
    config: Callable[[Env], Path]
    format: str  # "json" or "toml"
    path: tuple[str, ...]  # keys of the object or table that holds server entries
    entry: Callable[[list[str]], dict[str, Any]]
    cli: str | None
    cli_add: Callable[[list[str]], list[str]] | None
    cli_remove: list[str] | None
    skills: Callable[[Env], Path] | None
    reads: Callable[[Env], list[Path]]  # skill folders the harness loads
    duplicates: Callable[[Env], list[str]]

    def read_entry(self, env: Env) -> Any:
        """Return the knowledge-mcp entry, or None when the file or entry is missing.

        Raise `ConfigError` for TOML syntax errors or JSON structure errors.
        Malformed JSON strings or numbers can raise `json.JSONDecodeError`.
        """
        path = self.config(env)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        if self.format == "toml":
            return configedit.toml_entry(text, self.path[0], NAME)
        return configedit.json_entry(text, self.path, NAME)


def _claude_dir(env: Env) -> Path:
    return env.named("CLAUDE_CONFIG_DIR", env.home / ".claude")


def _claude_json(env: Env) -> Path:
    if env.environ.get("CLAUDE_CONFIG_DIR"):
        return _claude_dir(env) / ".claude.json"
    return env.home / ".claude.json"


def _codex_home(env: Env) -> Path:
    return env.named("CODEX_HOME", env.home / ".codex")


def _pi_dir(env: Env) -> Path:
    return env.named("PI_CODING_AGENT_DIR", env.home / ".pi" / "agent")


def _opencode_dir(env: Env) -> Path:
    return env.named("XDG_CONFIG_HOME", env.home / ".config") / "opencode"


def _opencode_config(env: Env) -> Path:
    folder = _opencode_dir(env)
    json_file, jsonc_file = folder / "opencode.json", folder / "opencode.jsonc"
    return jsonc_file if jsonc_file.is_file() and not json_file.is_file() else json_file


def _agents_skills(env: Env) -> Path:
    return env.home / ".agents" / "skills"


def _read_json(path: Path) -> Any:
    try:
        return configedit.json_value(path.read_text(encoding="utf-8"))
    except OSError, configedit.ConfigError:
        return None


def _claude_plugins(env: Env) -> list[str]:
    installed = _read_json(_claude_dir(env) / "plugins" / "installed_plugins.json")
    plugins = installed.get("plugins", {}) if isinstance(installed, dict) else {}
    return [
        f"Claude Code plugin {name}"
        for name in plugins
        if isinstance(name, str) and DUPLICATE.search(name.split("@")[0] + "@")
    ]


def _codex_plugins(env: Env) -> list[str]:
    try:
        config = tomllib.loads(
            (_codex_home(env) / "config.toml").read_text(encoding="utf-8")
        )
    except OSError, tomllib.TOMLDecodeError:
        return []
    plugins = config.get("plugins", {})
    return [
        f"Codex plugin {name}"
        for name, table in plugins.items()
        if DUPLICATE.search(name.split("@")[0] + "@")
        and not (isinstance(table, dict) and table.get("enabled") is False)
    ]


def _pi_packages(env: Env) -> list[str]:
    settings = _read_json(_pi_dir(env) / "settings.json")
    packages = settings.get("packages", []) if isinstance(settings, dict) else []
    found = []
    for package in packages:
        source = package.get("source") if isinstance(package, dict) else package
        if isinstance(source, str) and DUPLICATE.search(source):
            found.append(f"Pi package {source}")
    return found


def _opencode_plugins(env: Env) -> list[str]:
    config = _read_json(_opencode_config(env))
    plugins = config.get("plugin", []) if isinstance(config, dict) else []
    return [
        f"OpenCode plugin {name}"
        for name in plugins
        if isinstance(name, str) and DUPLICATE.search(name)
    ]


def _stdio(command: list[str]) -> dict[str, Any]:
    return {"command": command[0], "args": command[1:]}


# Codex forwards these variables, which set the state folder, to the server.
PASSED = [log.VARIABLE, "XDG_STATE_HOME"]


HARNESSES: dict[str, Harness] = {
    harness.id: harness
    for harness in (
        Harness(
            id="claude-code",
            title="Claude Code",
            config=_claude_json,
            format="json",
            path=("mcpServers",),
            entry=lambda command: {"type": "stdio", **_stdio(command)},
            cli="claude",
            cli_add=lambda command: [
                "mcp",
                "add",
                "--scope",
                "user",
                NAME,
                "--",
                *command,
            ],
            cli_remove=["mcp", "remove", "--scope", "user", NAME],
            skills=lambda env: _claude_dir(env) / "skills",
            reads=lambda env: [_claude_dir(env) / "skills"],
            duplicates=_claude_plugins,
        ),
        Harness(
            id="codex",
            title="Codex",
            config=lambda env: _codex_home(env) / "config.toml",
            format="toml",
            path=("mcp_servers",),
            entry=lambda command: {**_stdio(command), "env_vars": PASSED},
            cli=None,
            cli_add=None,
            cli_remove=None,
            skills=_agents_skills,
            reads=lambda env: [_agents_skills(env)],
            duplicates=_codex_plugins,
        ),
        Harness(
            id="claude-desktop",
            title="Claude desktop app",
            config=lambda env: (
                env.home
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            ),
            format="json",
            path=("mcpServers",),
            entry=_stdio,
            cli=None,
            cli_add=None,
            cli_remove=None,
            skills=None,
            reads=lambda _env: [],
            duplicates=lambda _env: [],
        ),
        Harness(
            id="pi",
            title="Pi",
            config=lambda env: _pi_dir(env) / "mcp.json",
            format="json",
            path=("mcpServers",),
            entry=_stdio,
            cli="pi",
            cli_add=lambda command: ["mcp", "add", NAME, "--", *command],
            cli_remove=["mcp", "remove", NAME],
            skills=_agents_skills,
            reads=lambda env: [_agents_skills(env), _pi_dir(env) / "skills"],
            duplicates=_pi_packages,
        ),
        Harness(
            id="opencode",
            title="OpenCode",
            config=_opencode_config,
            format="json",
            path=("mcp",),
            entry=lambda command: {
                "type": "local",
                "command": command,
                "enabled": True,
            },
            cli=None,
            cli_add=None,
            cli_remove=None,
            skills=_agents_skills,
            reads=lambda env: [
                _agents_skills(env),
                _opencode_dir(env) / "skills",
                _claude_dir(env) / "skills",
            ],
            duplicates=_opencode_plugins,
        ),
    )
}


def server_command(environ: dict[str, str] | None = None) -> list[str]:
    """Prefer an absolute `KNOWLEDGE_MCP_COMMAND`, then the running `kb` script, then
    `python -m knowledge_mcp`.
    """
    environment = os.environ if environ is None else environ
    named = environment.get("KNOWLEDGE_MCP_COMMAND", "")
    if os.path.isabs(named):
        return [named, "mcp"]
    script = Path(sys.argv[0])
    if script.name == "kb" and script.is_file():
        return [str(script.absolute()), "mcp"]
    return [sys.executable, "-m", "knowledge_mcp"]
