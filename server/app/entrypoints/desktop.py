# File: server/app/entrypoints/desktop.py
from __future__ import annotations

import argparse
import multiprocessing
from pathlib import Path

import uvicorn

from app.entrypoints._supervision import watch_parent
from app.factory import create_app
from app.settings import load_settings

DEFAULT_PORT = 8000


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="km-server", description="Pd·flow desktop backend"
    )
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument(
        "--store-root",
        type=Path,
        default=None,
        help="The folder holding the artifacts. May be unset; the app reports not-ready.",
    )
    parser.add_argument(
        "--principal-id",
        type=str,
        default=None,
        help="Who the local person is. Defaults to the OS login name.",
    )
    parser.add_argument("--knowledge-model-dir", type=Path, default=None)
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=None,
        help="Exit when this process goes away. The desktop shell passes its own pid.",
    )
    return parser.parse_args()


def main() -> None:
    multiprocessing.freeze_support()
    args = _parse_args()

    settings = load_settings(
        ROLE="desktop",
        PORT=args.port,
        HOST=args.host,
        STORE_ROOT=args.store_root,
        PRINCIPAL_ID=args.principal_id,
        KNOWLEDGE_MODEL_DIR=args.knowledge_model_dir,
    )

    watch_parent(args.parent_pid, "km-server")

    uvicorn.run(
        create_app(settings),
        host=settings.bind_host,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
