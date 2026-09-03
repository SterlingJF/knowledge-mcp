# File: server/app/factory.py
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.errors import KmError
from app.knowledge_model import KnowledgeModel, resolve_knowledge_model_dir
from app.middleware.logging_middleware import StructlogLoggingMiddleware
from app.roles import api_routers_for, root_routers_for
from app.settings import ALLOWED_HEADERS, EXPOSED_HEADERS, Settings
from app.store.vaults import VaultStores
from app.utilities.logging import configure_logging_on_startup, get_app_logger
from app.vault import layout

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_app_logger('factory')

TITLE = 'Km API'
VERSION = 'v1.0.0'


async def _km_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, KmError)  # noqa: S101
    payload: dict[str, Any] = {'detail': error.detail, 'errorCode': error.code}
    if error.fields:
        payload['fields'] = error.fields
    return JSONResponse(status_code=int(error.status), content=payload)


async def _unhandled_error_handler(_: Request, error: Exception) -> JSONResponse:
    logger.exception('Unhandled error', error=str(error))
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error', 'errorCode': 'INTERNAL_ERROR'},
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging_on_startup(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        model_dir = resolve_knowledge_model_dir(settings.KNOWLEDGE_MODEL_DIR)
        app.state.settings = settings
        app.state.knowledge_model = KnowledgeModel.load(model_dir)
        app.state.vaults = VaultStores(settings.STORE_ROOT, on_new_root=layout.ensure)

        ready, reason = app.state.vaults.default().is_ready()
        logger.info(
            'Application started',
            role=settings.ROLE,
            api_prefix=settings.API_PREFIX,
            knowledge_model_dir=str(model_dir),
            universes=len(app.state.knowledge_model.universes),
            storage_root=str(settings.STORE_ROOT) if settings.STORE_ROOT else None,
            storage_ready=ready,
            storage_detail=reason,
        )
        yield

    app = FastAPI(
        title=TITLE,
        version=VERSION,
        lifespan=lifespan,
        servers=[{'url': settings.API_PREFIX}],
    )

    # TestClient without lifespan.
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=list(ALLOWED_HEADERS),
        expose_headers=list(EXPOSED_HEADERS),
    )
    app.add_middleware(StructlogLoggingMiddleware, settings=settings)

    app.add_exception_handler(KmError, _km_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)

    for router in root_routers_for(settings.ROLE):
        app.include_router(router)
    for router in api_routers_for(settings.ROLE):
        app.include_router(router, prefix=settings.API_PREFIX)

    return app
