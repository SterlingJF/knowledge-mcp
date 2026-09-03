# File: server/app/routers/storage.py
"""Desktop-only routes (`app.roles`)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.config import (
    forget_store,
    read_config,
    remember_store,
    update_store_path,
)
from app.dependencies import FileStoreDep
from app.store.file_store import FileStore
from app.store.vaults import VaultStores

router = APIRouter(tags=['Storage'])

# `pdcp-0026` appends here.
STORAGE_OPTIONS: tuple[dict[str, Any], ...] = (
    {'type': 'filesystem', 'label': 'A folder on this computer'},
)


class StorageSelection(BaseModel):
    path: Path


class VaultCreation(BaseModel):
    parent: Path
    name: str


class VaultChange(BaseModel):
    """Rename, move, or both through one `Path.rename` call."""

    name: str | None = None
    parent: Path | None = None


def _vaults() -> list[dict[str, Any]]:
    entries = sorted(
        read_config().stores.items(),
        key=lambda item: item[1].last_opened,
        reverse=True,
    )
    return [
        {
            'id': identifier,
            'name': entry.display_name,
            'path': str(entry.path),
            'lastOpened': entry.last_opened,
            'open': entry.open,
            'available': FileStore(entry.path).is_ready()[0],
        }
        for identifier, entry in entries
    ]


def _state(store: FileStore) -> dict[str, Any]:
    ready, reason = store.is_ready()
    root = store.root
    return {
        'storageRoot': str(root) if root else None,
        'storageName': root.name if root else None,
        'storageReady': ready,
        'storageDetail': reason,
        'options': list(STORAGE_OPTIONS),
        'vaults': _vaults(),
    }


def _refusal(path: Path, reason: str | None) -> dict[str, Any]:
    return {
        'storageRoot': str(path),
        'storageName': path.name or None,
        'storageReady': False,
        'storageDetail': reason,
        'options': list(STORAGE_OPTIONS),
        'vaults': _vaults(),
    }


def _open(request: Request, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    remember_store(resolved)
    vaults: VaultStores = request.app.state.vaults
    vaults.set_default_root(resolved)
    return _state(vaults.for_root(resolved))


def _why_a_name_is_unusable(name: str) -> str | None:
    """Shared name check for create and rename."""
    separators = {os.sep, os.altsep} - {None}
    checks: tuple[tuple[bool, str], ...] = (
        (not name, 'A vault needs a name'),
        (
            name in {'.', '..'} or any(sep in name for sep in separators),
            'A vault name cannot contain a path separator',
        ),
    )
    return next((reason for failed, reason in checks if failed), None)


def _why_a_vault_cannot_be_made(parent: Path, name: str) -> str | None:
    name_fault = _why_a_name_is_unusable(name)
    if name_fault is not None:
        return name_fault
    checks: tuple[tuple[bool, str], ...] = (
        (not parent.exists(), f'The folder to create it in does not exist: {parent}'),
        (
            not parent.is_dir(),
            f'The folder to create it in is not a directory: {parent}',
        ),
        (
            not os.access(parent, os.W_OK),
            f'The folder to create it in is not writable: {parent}',
        ),
        ((parent / name).exists(), f'Something called {name} is already here'),
    )
    return next((reason for failed, reason in checks if failed), None)


def _why_a_vault_cannot_move(source: Path, target: Path) -> str | None:
    parent = target.parent
    checks: tuple[tuple[bool, str], ...] = (
        (not source.exists(), f"This vault's folder is not there any more: {source}"),
        (
            not os.access(source.parent, os.W_OK),
            f'The folder holding this vault is not writable: {source.parent}',
        ),
        (not parent.exists(), f'The folder to move it into does not exist: {parent}'),
        (
            not parent.is_dir(),
            f'The folder to move it into is not a directory: {parent}',
        ),
        (
            not os.access(parent, os.W_OK),
            f'The folder to move it into is not writable: {parent}',
        ),
        (
            target != source and target.exists(),
            f'Something called {target.name} is already here',
        ),
        (
            source in target.parents,
            'A vault cannot be moved inside itself',
        ),
    )
    return next((reason for failed, reason in checks if failed), None)


@router.get('/storage', include_in_schema=False)
async def get_storage(store: FileStoreDep) -> dict[str, Any]:
    """Current storage state."""
    return _state(store)


@router.put('/storage', include_in_schema=False)
async def put_storage(
    selection: StorageSelection,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Point the running store at an existing folder and remember it."""
    candidate = Path(selection.path).expanduser()
    ready, reason = FileStore(candidate).is_ready()

    if not ready:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(candidate, reason)

    return _open(request, candidate)


@router.post('/storage/vaults', include_in_schema=False)
async def create_vault(
    creation: VaultCreation,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Make a new vault folder, then open it."""
    parent = Path(creation.parent).expanduser()
    name = creation.name.strip()
    target = parent / name if name else parent

    refusal = _why_a_vault_cannot_be_made(parent, name)
    if refusal is not None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(target, refusal)

    try:
        target.mkdir(parents=False)
    except OSError as error:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(target, f'The vault could not be created: {error.strerror}')

    return _open(request, target)


@router.patch('/storage/vaults/{vault_id}', include_in_schema=False)
async def change_vault(
    vault_id: str,
    change: VaultChange,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Rename a vault's folder, move it, or both. Its id does not change."""
    entry = read_config().stores.get(vault_id)
    if entry is None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(Path(vault_id), f'No vault with id {vault_id}')

    source = entry.path
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
        else _why_a_name_is_unusable(name) or _why_a_vault_cannot_move(source, target)
    )
    if refusal is not None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(target, refusal)

    try:
        source.rename(target)
    except OSError as error:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(target, f'The vault could not be moved: {error.strerror}')

    update_store_path(vault_id, target)
    vaults: VaultStores = request.app.state.vaults
    vaults.rebind(source, target)
    return _state(vaults.for_root(target))


@router.delete('/storage/vaults/{vault_id}', include_in_schema=False)
async def remove_vault(
    vault_id: str,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Drop a vault from the list. Nothing on disk is touched."""
    entry = read_config().stores.get(vault_id)
    if entry is None:
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        return _refusal(Path(vault_id), f'No vault with id {vault_id}')

    forget_store(vault_id)
    vaults: VaultStores = request.app.state.vaults
    vaults.forget_root(entry.path)
    if vaults.default_root == entry.path:
        remaining = read_config().resolved_store()
        vaults.set_default_root(remaining.path if remaining else None)
    return _state(vaults.default())
