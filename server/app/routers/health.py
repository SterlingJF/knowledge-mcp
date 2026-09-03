# File: server/app/routers/health.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.dependencies import FileStoreDep

router = APIRouter(tags=['Health'])


@router.get('/health', include_in_schema=False)
async def health(request: Request) -> dict[str, Any]:
    return {'status': 'healthy', 'role': request.app.state.settings.ROLE}


@router.get('/ready', include_in_schema=False)
async def ready(
    request: Request, store: FileStoreDep, response: Response
) -> dict[str, Any]:
    settings = request.app.state.settings
    universes = len(request.app.state.knowledge_model.universes)

    store_ready, reason = store.is_ready()

    model_ready = universes > 0
    if not (store_ready and model_ready):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        'status': 'ready' if store_ready and model_ready else 'not-ready',
        'role': settings.ROLE,
        'storageRoot': str(store.root) if store.root else None,
        'storageReady': store_ready,
        'storageDetail': reason,
        'universesLoaded': universes,
    }


@router.get('/', include_in_schema=False)
async def root(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {
        'message': f'{settings.APP_NAME} ({settings.ROLE}) serving {settings.API_PREFIX}'
    }
