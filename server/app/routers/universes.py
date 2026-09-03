# File: server/app/routers/universes.py
"""Wire versions are strings (`app.knowledge_model.loader`). Guidance documents are optional."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.api_models_auto import (
    ErrorResponse,
    GuidanceDocument,
    UniverseDocument,
    UniverseSummary,
)
from app.dependencies import KnowledgeModelDep
from app.errors import NotFoundError

router = APIRouter(tags=['Universes'])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {'model': ErrorResponse},
    404: {'model': ErrorResponse},
}


@router.get(
    '/universes',
    response_model=list[UniverseSummary],
    responses={401: {'model': ErrorResponse}},
    summary='List the universes this image carries',
)
async def list_universes(model: KnowledgeModelDep) -> Any:
    return model.summaries()


@router.get(
    '/universes/{universeId}',
    response_model=UniverseDocument,
    responses=ERROR_RESPONSES,
    summary='Get one universe document in full',
)
async def get_universe_by_id(universeId: str, model: KnowledgeModelDep) -> Any:  # noqa: N803
    universe = model.universe(universeId)
    if universe is None:
        msg = f'This image carries no universe with id {universeId!r}'
        raise NotFoundError(msg)
    return universe.served_document()


@router.get(
    '/universes/{universeId}/guidance',
    response_model=GuidanceDocument,
    responses=ERROR_RESPONSES,
    summary='Get the type guidance for a universe',
)
async def get_universe_guidance(universeId: str, model: KnowledgeModelDep) -> Any:  # noqa: N803
    if model.universe(universeId) is None:
        msg = f'This image carries no universe with id {universeId!r}'
        raise NotFoundError(msg)
    guidance = model.guidance.get(universeId)
    if guidance is None:
        msg = f'Universe {universeId!r} has no guidance document in this image'
        raise NotFoundError(msg)
    return guidance.served_document()
