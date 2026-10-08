# File: mcp-server/app/entrypoints/_supervision.py
"""Exit when the parent process exits. Copy of `server/app/entrypoints/_supervision.py`."""

from __future__ import annotations

import contextlib
import os
import signal
import threading
import time

POLL_SECONDS = 2.0
GRACE_SECONDS = 3.0


def _orphaned(parent_pid: int) -> bool:
    if os.getppid() == 1:
        return True
    try:
        os.kill(parent_pid, 0)
    except OSError:
        return True
    return False


def _watch(parent_pid: int, name: str) -> None:
    while True:
        time.sleep(POLL_SECONDS)
        if not _orphaned(parent_pid):
            continue

        # Signal before print. Print can raise.
        os.kill(os.getpid(), signal.SIGTERM)
        # stdout pipe dies with parent.
        with contextlib.suppress(OSError):
            print(f"[{name}] parent {parent_pid} is gone -> shutting down", flush=True)

        time.sleep(GRACE_SECONDS)
        os._exit(0)


def watch_parent(parent_pid: int | None, name: str) -> None:
    if not parent_pid:
        return
    thread = threading.Thread(
        target=_watch, args=(parent_pid, name), name="parent-watchdog", daemon=True
    )
    thread.start()
