# File: server/app/utilities/logging.py
from __future__ import annotations

import inspect
import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from structlog.typing import Processor

    from app.settings import Settings

APP_LOGGER_NAMESPACE = 'km-server'


def get_app_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    if name:
        return structlog.get_logger(f'{APP_LOGGER_NAMESPACE}.{name}')

    frame = inspect.currentframe()
    caller = frame.f_back if frame else None
    module_name = (
        caller.f_globals.get('__name__', 'unknown_module')
        if caller
        else 'unknown_caller'
    )
    bare = module_name.split('.')[-1]
    if bare == '__main__':
        bare = 'main_script'
    return structlog.get_logger(f'{APP_LOGGER_NAMESPACE}.{bare}')


def configure_logging_on_startup(settings: Settings) -> None:
    level_name = settings.LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)

    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt='iso', utc=True),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    is_tty = sys.stdout.isatty()
    as_json = (not is_tty) or settings.FORCE_JSON_LOGS
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if as_json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(processor=renderer))
    handler.setLevel(level)

    root = logging.getLogger(APP_LOGGER_NAMESPACE)
    for existing in root.handlers[:]:
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False

    # Request logs come from middleware (server/app/middleware/logging_middleware.py).
    for silenced in ('uvicorn.error', 'uvicorn.access'):
        logging.getLogger(silenced).handlers = []
        logging.getLogger(silenced).propagate = False
    logging.getLogger('uvicorn.asgi').handlers = []
    logging.getLogger('uvicorn.asgi').propagate = True

    get_app_logger('config.logging').info(
        'Application logging configured.',
        log_level=level_name,
        json_output=as_json,
        tty_detected=is_tty,
        role=settings.ROLE,
    )
