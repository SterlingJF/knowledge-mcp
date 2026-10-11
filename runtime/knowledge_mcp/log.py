"""One JSON Lines entry per tool answer, in knowledge-mcp's own state folder.

The edit record (`knowledge_mcp.edits`) keeps its own JSON Lines file in the same folder.

The folder is the one `KNOWLEDGE_MCP_STATE_DIR` names, else `$XDG_STATE_HOME/knowledge-mcp`, else
`~/.local/state/knowledge-mcp`. `directory` alone resolves the folder; the log, the edit record,
Explorer and `kb setup` all call `directory`. Codex starts the server with HOME, a few other names
and the names its entry lists, so the default needs only HOME.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Names the state folder; a host that clears the environment must pass the name through.
VARIABLE = "KNOWLEDGE_MCP_STATE_DIR"

_lock = threading.Lock()


def _absolute(value: str) -> Path | None:
    """The folder an absolute value names, `~` expanded; None for an empty or relative value."""
    expanded = os.path.expanduser(value)
    return Path(expanded) if os.path.isabs(expanded) else None


def directory(
    environ: Mapping[str, str] | None = None, home: Path | None = None
) -> Path:
    """The state folder: `$KNOWLEDGE_MCP_STATE_DIR`, else the XDG one, else the one under HOME."""
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
    """SHA-256 of the arguments as sent, keys sorted, no spaces."""
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return text_digest(canonical)


def text_digest(text: str) -> str:
    """SHA-256 of the text as UTF-8, prefixed `sha256:`."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def now() -> str:
    """The current UTC time, to the millisecond, ending in Z."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append(name: str, entry: dict[str, Any]) -> None:
    """Append one JSON line to `name` in the state folder, readable by the user alone."""
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
    """Append the time, the tool, the location text, a digest of the arguments and every text returned."""
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
