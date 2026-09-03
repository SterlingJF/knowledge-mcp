# File: server/app/routers/vaults.py
"""Desktop client uses `app.routers.storage` (`launcher/src/lib/backend.ts`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.api_models_auto import (
    Vault,
    VaultChange,
    VaultCreation,
    VaultRefusal,
    VaultSelection,
)
from app.store.vaults import VaultStores
from app.vault import service

router = APIRouter(tags=['Vaults'])


def _refused(response: Response, path: Path, reason: str) -> VaultRefusal:
    """Refusal with contract status."""
    response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return VaultRefusal(path=str(path), reason=reason)


def _activate(request: Request, path: Path) -> None:
    """Set default for requests without `X-Km-Vault` (`VaultStores.resolve`)."""
    vaults: VaultStores = request.app.state.vaults
    vaults.set_default_root(path.resolve())


@router.get('/vaults')
async def list_vaults() -> list[Vault]:
    """Every remembered vault, most recently opened first."""
    return service.listed()


@router.post('/vaults', status_code=status.HTTP_201_CREATED)
async def create_vault(
    creation: VaultCreation,
    request: Request,
    response: Response,
) -> Any:
    """Make a vault folder, give it its folders, and open it."""
    parent = Path(creation.parent).expanduser()
    name = creation.name.strip()

    refusal = service.why_a_vault_cannot_be_made(parent, name)
    if refusal is not None:
        return _refused(response, parent / name if name else parent, refusal)

    try:
        target = service.make(parent, name)
    except OSError as error:
        return _refused(
            response,
            parent / name,
            f'The vault could not be created: {error.strerror}',
        )

    _, vault = service.remember(target)
    _activate(request, target)
    return vault


@router.post('/vaults/open')
async def open_vault(
    selection: VaultSelection,
    request: Request,
    response: Response,
) -> Any:
    """Adopt an existing folder as a vault. Absent folders are created, the rest left alone."""
    candidate = Path(selection.path).expanduser()

    refusal = service.why_a_folder_cannot_be_opened(candidate)
    if refusal is not None:
        return _refused(response, candidate, refusal)

    _, vault = service.remember(candidate)
    _activate(request, candidate)
    return vault


@router.get('/vaults/{vault_id}')
async def get_vault_by_id(vault_id: str, response: Response) -> Any:
    """One vault, or 404."""
    vault = service.one(vault_id)
    if vault is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return None
    return vault


@router.patch('/vaults/{vault_id}')
async def change_vault(
    vault_id: str,
    change: VaultChange,
    request: Request,
    response: Response,
) -> Any:
    """Rename a vault's folder, move it, or both. Its id does not change."""
    entry = service.one(vault_id)
    if entry is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return None

    source = Path(entry.path)
    name = (change.name if change.name is not None else source.name).strip()
    parent = (
        Path(change.parent).expanduser().resolve()
        if change.parent is not None
        else source.parent
    )
    target = parent / name if name else parent

    refusal = (
        'A vault change has to say what to change'
        if change.name is None and change.parent is None
        else service.why_a_name_is_unusable(name)
        or service.why_a_vault_cannot_move(source, target)
    )
    if refusal is not None:
        return _refused(response, target, refusal)

    try:
        vault = service.move(vault_id, source, target)
    except OSError as error:
        return _refused(
            response, target, f'The vault could not be moved: {error.strerror}'
        )

    vaults: VaultStores = request.app.state.vaults
    vaults.rebind(source, target)
    return vault


@router.delete('/vaults/{vault_id}')
async def forget_vault(vault_id: str, request: Request) -> Response:
    """Drop a vault from the list. Nothing on disk is touched."""
    entry = service.one(vault_id)
    if entry is None:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    path = Path(entry.path)
    service.forget(vault_id)
    vaults: VaultStores = request.app.state.vaults
    vaults.forget_root(path)
    if vaults.default_root == path:
        remaining = service.listed()
        vaults.set_default_root(Path(remaining[0].path) if remaining else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
