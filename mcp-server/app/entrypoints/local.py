# File: mcp-server/app/entrypoints/local.py
"""The entry point PyInstaller freezes."""

from __future__ import annotations

import argparse
import multiprocessing

import uvicorn

from app import km_api
from app.entrypoints._supervision import watch_parent
from app.server import build_app, describe
from app.settings import load_settings


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="knowledge-mcp", description="Pd·flow model-context server"
    )
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", type=str, default=None)
    parser.add_argument(
        "--api-origin",
        type=str,
        default=None,
        help=(
            "Where the backend is, including the API prefix. The one address this server "
            "needs. Example: http://127.0.0.1:17921/api/v1"
        ),
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=None,
        help=(
            "Exit when this process goes away. The desktop shell passes its own pid. Leave it "
            "unset to run unsupervised."
        ),
    )
    return parser.parse_args()


def main() -> None:
    multiprocessing.freeze_support()
    args = _parse_args()

    settings = load_settings(
        PORT=args.port,
        HOST=args.host,
        API_ORIGIN=args.api_origin,
    )

    km_api.configure(settings)
    watch_parent(args.parent_pid, "knowledge-mcp")

    print(f"[mcp] {describe(settings)}", flush=True)
    print(f"[mcp] backend {km_api.probe()}", flush=True)

    uvicorn.run(
        build_app(settings),
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,
    )


if __name__ == "__main__":
    main()
