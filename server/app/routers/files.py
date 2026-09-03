from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api_models_auto import ErrorResponse
from app.dependencies import FileStoreDep
from app.store.file_store import StoredFile

router = APIRouter(tags=['Files'])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {'model': ErrorResponse},
    422: {'model': ErrorResponse},
    503: {'model': ErrorResponse},
}


class FileSummary(BaseModel):
    path: str
    absolutePath: str
    size: int
    modifiedAt: datetime


class FileContent(FileSummary):
    content: str | None


def _summary(stored: StoredFile) -> dict[str, Any]:
    return {
        'path': stored.relative_path,
        'absolutePath': str(stored.path.absolute()),
        'size': stored.size,
        'modifiedAt': stored.modified_at,
    }


@router.get(
    '/files',
    response_model=list[FileSummary],
    responses=ERROR_RESPONSES,
    summary='List vault files',
)
async def list_files(store: FileStoreDep) -> Any:
    return [_summary(stored) for stored in store.files()]


@router.get(
    '/files/{filePath:path}',
    response_model=FileContent,
    responses=ERROR_RESPONSES,
    summary='Read a vault file',
)
async def read_file(filePath: str, store: FileStoreDep) -> Any:  # noqa: N803
    stored, content = store.read_file(filePath)
    return {**_summary(stored), 'content': content}
