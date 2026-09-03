# File: server/app/utilities/atomic_write.py
from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEMP_PREFIX = '.knowledge-mcp-'


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=str(path.parent), prefix=TEMP_PREFIX, suffix='.tmp'
    )
    try:
        with os.fdopen(handle, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
