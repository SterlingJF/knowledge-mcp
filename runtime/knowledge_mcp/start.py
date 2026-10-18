"""Plugin entry point: install `requirements.lock` into a cached environment, then run the server."""

# Standard library only: this module runs before any dependency is installed.
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
LOCK = PLUGIN / "requirements.lock"


def cache() -> Path:
    """Use `$XDG_CACHE_HOME/knowledge-mcp/environments` when XDG_CACHE_HOME is absolute.
    Otherwise use `~/.cache/knowledge-mcp/environments`."""
    base = os.environ.get("XDG_CACHE_HOME", "")
    root = Path(base) if os.path.isabs(base) else Path.home() / ".cache"
    return root / "knowledge-mcp" / "environments"


def interpreter(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _uv(*args: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        sys.exit(
            "Error: uv is not on PATH.\nInstall uv from https://docs.astral.sh/uv/."
        )
    # MCP messages use stdout, so uv's output goes to stderr.
    done = subprocess.run([uv, *args], stdout=sys.stderr, check=False)
    if done.returncode != 0:
        sys.exit(done.returncode)


def environment() -> Path:
    """Build the cached environment when its Python executable is missing."""
    key = hashlib.sha256(LOCK.read_bytes() + sys.version.encode()).hexdigest()[:16]
    target = cache() / key
    if interpreter(target).is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{key}-", dir=target.parent))
    try:
        _uv(
            "venv",
            "--quiet",
            "--relocatable",
            "--allow-existing",
            "--python",
            sys.executable,
            str(stage),
        )
        # `uv pip sync` rejects any download whose hash is not in requirements.lock.
        _uv("pip", "sync", "--quiet", "--python", str(interpreter(stage)), str(LOCK))
        try:
            stage.rename(target)
        except OSError:
            # Another session may have built the same environment first.
            if not interpreter(target).is_file():
                raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return target


def main() -> None:
    python = str(interpreter(environment()))
    os.chdir(PLUGIN)
    if os.name == "nt":
        sys.exit(
            subprocess.run([python, "-m", "knowledge_mcp"], check=False).returncode
        )
    os.execv(python, [python, "-m", "knowledge_mcp"])


if __name__ == "__main__":
    main()
