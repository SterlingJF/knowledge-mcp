# File: server/app/middleware/logging_middleware.py
"""Request actors are bound by `app.context`."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from app.utilities.logging import get_app_logger

if TYPE_CHECKING:
    from fastapi import Request
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.responses import Response

    from app.settings import Settings

HEADER_REQUEST_ID = "X-Request-ID"


class StructlogLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._low_noise = settings.LOW_NOISE_PATHS

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        structlog.contextvars.clear_contextvars()

        request_id = request.headers.get(HEADER_REQUEST_ID) or str(uuid.uuid4())
        client = request.client
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            http_method=request.method,
            http_path=str(request.url.path),
            http_client_addr=f"{client.host}:{client.port}" if client else "unknown",
            km_client=request.headers.get("X-Km-Client", "unknown"),
        )

        access_logger = get_app_logger("access")
        log = (
            access_logger.debug
            if request.url.path in self._low_noise
            else access_logger.info
        )
        log("Request received")

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            structlog.contextvars.bind_contextvars(
                http_status_code=500,
                http_response_duration_ms=round(
                    (time.perf_counter() - started) * 1000, 2
                ),
            )
            access_logger.exception("Unhandled exception during request processing")
            raise

        structlog.contextvars.bind_contextvars(
            http_status_code=response.status_code,
            http_response_duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        log("Request finished")

        response.headers[HEADER_REQUEST_ID] = request_id
        return response
