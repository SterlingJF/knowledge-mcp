# File: server/app/routers/artifacts.py
"""Payload validation uses generated contract models with `extra='forbid'` (app.api_models_auto)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response, status

from app.api_models_auto import (
    Artifact,
    ArtifactCreationPayload,
    ArtifactStatusEnum,
    ArtifactStatusTransitionPayload,
    ArtifactSummary,
    ArtifactUpdatePayload,
    ErrorResponse,
)
from app.context import RequestContextDep
from app.dependencies import ArtifactServiceDep
from app.errors import PreconditionRequiredError

router = APIRouter(tags=["Artifacts"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    428: {"model": ErrorResponse},
}


def _with_etag(response: Response, etag: str) -> None:
    response.headers["ETag"] = etag


@router.post(
    "/artifacts",
    response_model=Artifact,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Create an artifact",
)
async def create_artifact(
    payload: ArtifactCreationPayload,
    context: RequestContextDep,
    service: ArtifactServiceDep,
    response: Response,
) -> Any:
    artifact, etag = service.create(
        payload.model_dump(mode="json", exclude_unset=True), context
    )
    _with_etag(response, etag)
    return artifact


@router.get(
    "/artifacts",
    response_model=list[ArtifactSummary],
    responses=ERROR_RESPONSES,
    summary="List artifacts",
)
async def list_artifact_summaries(
    service: ArtifactServiceDep,
    projectId: Annotated[str | None, Query()] = None,  # the wire is camelCase
    artifactType: Annotated[str | None, Query()] = None,
    status_filter: Annotated[ArtifactStatusEnum | None, Query(alias="status")] = None,
    orderingFrameValue: Annotated[str | None, Query()] = None,
) -> Any:
    return service.list_summaries(
        project_id=projectId,
        artifact_type=artifactType,
        status=status_filter.value if status_filter else None,
        ordering_frame_value=orderingFrameValue,
    )


@router.get(
    "/artifacts/{artifactId}",
    response_model=Artifact,
    responses=ERROR_RESPONSES,
    summary="Get one artifact in full",
)
async def get_artifact_by_id(
    artifactId: str,
    service: ArtifactServiceDep,
    response: Response,
) -> Any:
    artifact, etag = service.get(artifactId)
    _with_etag(response, etag)
    return artifact


@router.put(
    "/artifacts/{artifactId}",
    response_model=Artifact,
    responses=ERROR_RESPONSES,
    summary="Update an artifact",
)
async def update_artifact(
    artifactId: str,
    payload: ArtifactUpdatePayload,
    context: RequestContextDep,
    service: ArtifactServiceDep,
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Any:
    if if_match is None:
        msg = "Read the artifact and send its ETag in If-Match before updating it"
        raise PreconditionRequiredError(msg)
    async with service.store.lock_for(artifactId):
        artifact, etag = service.update(
            artifactId,
            payload.model_dump(mode="json", exclude_unset=True),
            context,
            if_match,
        )
    _with_etag(response, etag)
    return artifact


@router.delete(
    "/artifacts/{artifactId}",
    status_code=status.HTTP_204_NO_CONTENT,
    # FastAPI `NoneType` response-model inference for body-less 204.
    response_model=None,
    responses=ERROR_RESPONSES,
    summary="Delete an artifact",
)
async def delete_artifact(
    artifactId: str,
    service: ArtifactServiceDep,
) -> None:
    async with service.store.lock_for(artifactId):
        service.delete(artifactId)


@router.post(
    "/artifacts/{artifactId}/status",
    response_model=Artifact,
    responses=ERROR_RESPONSES,
    summary="Move an artifact between draft and committed",
)
async def transition_artifact_status(
    artifactId: str,
    payload: ArtifactStatusTransitionPayload,
    context: RequestContextDep,
    service: ArtifactServiceDep,
    response: Response,
) -> Any:
    async with service.store.lock_for(artifactId):
        artifact, etag = service.transition_status(
            artifactId, payload.status.value, context
        )
    _with_etag(response, etag)
    return artifact
