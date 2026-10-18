"""Run kbp in kb's own process for `kb kbp`, and in a child process for tools and `kb doctor`."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from knowledge_mcp import bundled, problems
from knowledge_mcp.errors import REINSTALL

TIMEOUT_SECONDS = 120

KINDS = ("knowledge-bus/kinds/1", "knowledge-bus/kinds-set/1")
CARD = ("knowledge-bus/card/1",)
EXPLORER_MODEL = ("knowledge-bus/explorer-model/1",)

KbpMissing = problems.KbpMissing


@dataclass(frozen=True)
class Printed:
    stdout: str
    stderr: str
    code: int


def cli() -> ModuleType:
    """Raise KbpMissing when kbp is not installed."""
    try:
        return importlib.import_module("kbp_conform.cli")
    except ImportError as error:
        message = "kbp is missing from this kb install."
        raise KbpMissing(message) from error


def call(argv: list[str]) -> int:
    """Share kb's working directory, stdin, stdout and stderr with kbp.

    Add the `explorer_bundle()` variables to `os.environ` before kbp starts.
    """
    main = cast("Callable[[list[str]], int]", cli().main)
    os.environ.update(explorer_bundle())
    return main(argv)


def explorer_bundle() -> dict[str, str]:
    """Environment variables that point `kbp --explore` at the bundled viewer.

    The knowledge-bus wheel ships no viewer.
    """
    return {
        "KNOWLEDGE_BUS_EXPLORER_BUNDLE": str(bundled.EXPLORER / "explorer-viewer.js"),
        "KNOWLEDGE_BUS_EXPLORER_BUNDLE_MANIFEST": str(
            bundled.EXPLORER / "explorer-viewer.json"
        ),
    }


def run(argv: list[str], cwd: Path, **env: str) -> Printed:
    # Raise KbpMissing here rather than start a child that cannot import kbp.
    cli()
    done = subprocess.run(
        # -P keeps the working directory off the child's import path, so a .py file there cannot
        # shadow a module.
        [sys.executable, "-P", "-m", "kbp_conform.cli", *argv],
        stdin=subprocess.DEVNULL,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", **env, **explorer_bundle()},
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    return Printed(done.stdout, done.stderr, done.returncode)


def parsed(output: Printed, mode: str, expected: tuple[str, ...]) -> dict[str, Any]:
    """Raise KbpVersionSkew unless the output is a JSON object whose `schema` is in `expected`."""
    reads = " and ".join(expected)
    try:
        data = json.loads(output.stdout)
    except ValueError:
        data = None
    found = data.get("schema") if isinstance(data, dict) else None
    if not isinstance(data, dict) or found not in expected:
        printed = f"schema {found}" if found is not None else "no schema value"
        msg = (
            f"kbp --{mode} printed {printed}, but knowledge-mcp reads {reads}. The installed "
            f"kbp version does not match this knowledge-mcp. {REINSTALL}"
        )
        raise problems.KbpVersionSkew(msg)
    return data
