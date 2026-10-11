"""The installed `kbp` console script, run as is."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# A kbp run reads a handful of small files; anything longer has hung.
TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class Printed:
    """What kbp printed, and its exit code."""

    stdout: str
    stderr: str
    code: int


def executable() -> Path:
    """The `kbp` script installed beside this interpreter, else the one on PATH."""
    name = "kbp.exe" if os.name == "nt" else "kbp"
    beside = Path(sys.executable).parent / name
    if beside.is_file():
        return beside
    found = shutil.which("kbp")
    if found is None:
        msg = "The kbp console script is missing; install the knowledge-bus package."
        raise RuntimeError(msg)
    return Path(found)


def environment(**extra: str) -> dict[str, str]:
    """This process's environment, with UTF-8 output and any extra names."""
    return {**os.environ, "PYTHONIOENCODING": "utf-8", **extra}


def run(argv: list[str], cwd: Path, **env: str) -> Printed:
    done = subprocess.run(
        [str(executable()), *argv],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=environment(**env),
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    return Printed(done.stdout, done.stderr, done.returncode)
