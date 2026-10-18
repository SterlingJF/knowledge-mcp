"""The tool log, `log.jsonl`, and the location of the state folder."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VARIABLE = "KNOWLEDGE_MCP_STATE_DIR"

_lock = threading.Lock()


def _absolute(value: str) -> Path | None:
    """The value as a Path after `~` expansion, or None when the value is empty or relative."""
    expanded = os.path.expanduser(value)
    return Path(expanded) if os.path.isabs(expanded) else None


def directory(
    environ: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """`$KNOWLEDGE_MCP_STATE_DIR`, else `$XDG_STATE_HOME/knowledge-mcp`, else
    `~/.local/state/knowledge-mcp`.

    Skips empty and relative values.
    """
    environ = os.environ if environ is None else environ
    named = _absolute(environ.get(VARIABLE, ""))
    if named is not None:
        return named
    state = _absolute(environ.get("XDG_STATE_HOME", ""))
    if state is None:
        state = (Path.home() if home is None else home) / ".local" / "state"
    return state / "knowledge-mcp"


def path() -> Path:
    return directory() / "log.jsonl"


def digest(arguments: dict[str, Any]) -> str:
    """Hash JSON with sorted keys and no whitespace between tokens."""
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return text_digest(canonical)


def text_digest(text: str) -> str:
    """SHA-256 of the text as UTF-8, prefixed `sha256:`."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def now() -> str:
    """The current UTC time, to the millisecond, ending in Z."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append(name: str, entry: dict[str, Any]) -> None:
    """Append one JSON line to `name` in the state folder.

    Create a missing folder with mode 0700 and a missing file with mode 0600.
    """
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with _lock:
        directory().mkdir(parents=True, exist_ok=True, mode=0o700)
        handle = os.open(
            directory() / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
        )
        try:
            os.write(handle, line.encode("utf-8"))
        finally:
            os.close(handle)


def record(
    tool: str, location: str, arguments: dict[str, Any], returned: list[str]
) -> None:
    """Store a digest of the arguments, never the arguments themselves."""
    append(
        path().name,
        {
            "time": now(),
            "tool": tool,
            "location": location,
            "sent": digest(arguments),
            "returned": returned,
        },
    )
