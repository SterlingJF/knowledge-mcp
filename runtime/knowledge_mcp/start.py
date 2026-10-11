"""Start the server from `requirements.lock`, every hashed file checked: `python -m knowledge_mcp.start`.

Both host manifests run this with uv. It needs only the standard library, so it runs before any
dependency is installed. It builds one virtual environment per lock and Python in
knowledge-mcp's cache folder with `uv pip sync`, which refuses a file whose hash differs from the
lock, then runs `python -m knowledge_mcp` from that environment. Later starts reuse the environment.
"""

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
    """`$XDG_CACHE_HOME/knowledge-mcp/environments`, else `~/.cache/knowledge-mcp/environments`."""
    base = os.environ.get("XDG_CACHE_HOME", "")
    root = Path(base) if os.path.isabs(base) else Path.home() / ".cache"
    return root / "knowledge-mcp" / "environments"


def interpreter(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _uv(*args: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        sys.exit("knowledge-mcp needs uv: https://docs.astral.sh/uv/")
    # stdout carries MCP messages, so uv reports on stderr.
    done = subprocess.run([uv, *args], stdout=sys.stderr, check=False)
    if done.returncode != 0:
        sys.exit(done.returncode)


def environment() -> Path:
    """The environment for this lock and this Python, built once."""
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
        _uv("pip", "sync", "--quiet", "--python", str(interpreter(stage)), str(LOCK))
        try:
            stage.rename(target)
        except OSError:
            # Another session built the same environment first.
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
