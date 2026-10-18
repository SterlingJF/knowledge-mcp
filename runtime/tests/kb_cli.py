from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from mcp.client.stdio import StdioServerParameters

from tests.harness import MODULE

# Use a stable registration path without invoking the installed executable.
KB = "/opt/homebrew/bin/kb"
HARNESSES = ["claude-code", "codex", "claude-desktop", "pi", "opencode"]
KBP = Path(sys.executable).parent / "kbp"

COMMANDS = ["doctor", "kbp", "mcp", "setup", "type"]
KBP_MODES = ["validate", "self-check", "mint", "inspect", "explore", "card", "kinds"]
KBP_MODE_FLAGS = {
    "validate": set(),
    "self-check": set(),
    "mint": set(),
    "inspect": {"--universe"},
    "explore": {"--output", "--universe", "--replace"},
    "card": {"--universe", "--format"},
    "kinds": {"--universe", "--format"},
}
HELP_PAGES: list[tuple[str, ...]] = [
    (),
    *[(command,) for command in COMMANDS],
    *[("kbp", mode) for mode in KBP_MODES],
]

KNOWLEDGE_BUS_SKILLS = {
    "kb-check",
    "kb-evolve",
    "kb-explore",
    "kb-ingest",
    "kb-uncover-question",
    "kb-uncover-decision",
}
SKILLS = MODULE / "skills"


def run_kb(
    home: Path,
    *args: str,
    cwd: Path | None = None,
    path: str = "",
    **env: str,
) -> subprocess.CompletedProcess[str]:
    """Start kb with an isolated environment, closed stdin and the supplied PATH."""
    return subprocess.run(
        [sys.executable, "-m", "knowledge_mcp.cli", *args],
        cwd=cwd or MODULE,
        env={
            "HOME": str(home),
            "PATH": path,
            "KNOWLEDGE_MCP_COMMAND": KB,
            "PYTHONIOENCODING": "utf-8",
            **env,
        },
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def kbp_env(**extra: str) -> dict[str, str]:
    return {**os.environ, "PYTHONIOENCODING": "utf-8", **extra}


def run_kbp(
    home: Path, *args: str, cwd: Path, **env: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(KBP), *args],
        cwd=cwd,
        env={"HOME": str(home), "PATH": "", "PYTHONIOENCODING": "utf-8", **env},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def kb_mcp(root: Path) -> StdioServerParameters:
    (root / "home").mkdir(parents=True, exist_ok=True)
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "knowledge_mcp.cli", "mcp"],
        cwd=MODULE,
        env={
            "HOME": str(root / "home"),
            "XDG_STATE_HOME": str(root / "state"),
            "PATH": os.environ["PATH"],
        },
    )


def sections(page: str) -> dict[str, list[str]]:
    """Exclude wrapped descriptions by keeping entries at the smallest indent in each section."""
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in page.splitlines():
        if line and not line[0].isspace():
            current = None
            if line.rstrip().endswith(":"):
                current = found.setdefault(line.strip()[:-1].lower(), [])
            continue
        if current is not None and line.strip():
            current.append(line)
    for name, lines in found.items():
        indent = min((len(line) - len(line.lstrip()) for line in lines), default=0)
        found[name] = [
            line for line in lines if len(line) - len(line.lstrip()) == indent
        ]
    return found


def listed_commands(page: str) -> set[str]:
    names = set()
    for heading, lines in sections(page).items():
        if "command" in heading or "mode" in heading:
            for line in lines:
                match = re.match(r"\s+([a-z][a-z0-9-]*)(?:\s{2,}|\s*$)", line)
                if match:
                    names.add(match.group(1))
    return names


def listed_flags(page: str) -> set[str]:
    flags = set()
    for heading, lines in sections(page).items():
        if "option" in heading or "flag" in heading:
            for line in lines:
                spec = line.strip()
                if spec.startswith("-"):
                    flags |= set(re.findall(r"--[a-z][a-z0-9-]*", spec.split("  ")[0]))
    return flags


def did_you_mean(stderr: str, name: str) -> bool:
    token = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
    return any(
        "Did you mean" in line and re.search(token, line.split("Did you mean", 1)[1])
        for line in stderr.splitlines()
    )


def error_lines(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if line.startswith("Error:")]


def next_line(stderr: str) -> str:
    """Return an empty string when no line follows the first Error: line."""
    lines = stderr.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Error:"):
            return lines[index + 1].strip() if index + 1 < len(lines) else ""
    return ""


def example_faults(page: str, commands: list[str], before: str) -> list[str]:
    """Require examples before the named heading, beneath # comments, without shell prompts."""
    lines = [line.strip() for line in page.splitlines()]
    faults = []
    heading = next(
        (index for index, line in enumerate(lines) if line == f"{before}:"), None
    )
    if heading is None:
        faults.append(f"no {before}: heading")
    for command in commands:
        if command not in lines:
            faults.append(f"no example line {command!r}")
            continue
        index = lines.index(command)
        above = index - 1
        while above >= 0 and lines[above].startswith("kb "):
            above -= 1
        if above < 0 or not lines[above].startswith("# "):
            faults.append(f"{command!r} sits under no # comment")
        if heading is not None and index > heading:
            faults.append(f"{command!r} comes after {before}:")
    faults += [f"prompt in {line!r}" for line in lines if line.startswith("$ ")]
    return faults


EXIT_CODES = re.compile(r"^Exit codes: 0 \S.*, 1 \S.*, 2 \S.*\.$")


def last_line(page: str) -> str:
    return next(
        (line.strip() for line in reversed(page.splitlines()) if line.strip()), ""
    )
