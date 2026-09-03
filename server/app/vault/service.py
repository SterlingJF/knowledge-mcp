# File: server/app/vault/service.py
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.api_models_auto import (
    Vault as VaultModel,
)
from app.api_models_auto import (
    VaultFolder,
    VaultFolderName,
    VaultId,
)
from app.config import (
    forget_store,
    read_config,
    remember_store,
    update_store_path,
)
from app.vault import layout

if TYPE_CHECKING:
    from pathlib import Path


def is_usable(root: Path) -> bool:
    return root.exists() and root.is_dir() and os.access(root, os.R_OK | os.W_OK)


def _folders(root: Path) -> list[VaultFolder]:
    return [
        VaultFolder(name=VaultFolderName(folder.name), adopted=folder.adopted)
        for folder in layout.inspect(root)
    ]


def _as_model(identifier: str, entry: object, folders: list[VaultFolder]) -> VaultModel:
    path = entry.path  # type: ignore[attr-defined]
    return VaultModel(
        id=VaultId(identifier),
        name=path.name,
        path=str(path),
        folders=folders,
        available=is_usable(path),
        lastOpened=entry.last_opened,  # type: ignore[attr-defined]
        open=entry.open,  # type: ignore[attr-defined]
    )


def listed() -> list[VaultModel]:
    entries = sorted(
        read_config().stores.items(),
        key=lambda item: item[1].last_opened,
        reverse=True,
    )
    return [
        _as_model(identifier, entry, _folders(entry.path))
        for identifier, entry in entries
    ]


def one(identifier: str) -> VaultModel | None:
    entry = read_config().stores.get(identifier)
    if entry is None:
        return None
    return _as_model(identifier, entry, _folders(entry.path))


def why_a_name_is_unusable(name: str) -> str | None:
    separators = {os.sep, os.altsep} - {None}
    checks: tuple[tuple[bool, str], ...] = (
        (not name, 'A vault needs a name'),
        (
            name in {'.', '..'} or any(sep in name for sep in separators),
            'A vault name cannot contain a path separator',
        ),
    )
    return next((reason for failed, reason in checks if failed), None)


def why_a_vault_cannot_be_made(parent: Path, name: str) -> str | None:
    name_fault = why_a_name_is_unusable(name)
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


def why_a_folder_cannot_be_opened(path: Path) -> str | None:
    checks: tuple[tuple[bool, str], ...] = (
        (not path.exists(), f'That folder does not exist: {path}'),
        (not path.is_dir(), f'That is not a folder: {path}'),
        (
            not os.access(path, os.R_OK | os.W_OK),
            f'That folder is not readable and writable: {path}',
        ),
    )
    return next((reason for failed, reason in checks if failed), None)


def why_a_vault_cannot_move(source: Path, target: Path) -> str | None:
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
        (source in target.parents, 'A vault cannot be moved inside itself'),
    )
    return next((reason for failed, reason in checks if failed), None)


def make(parent: Path, name: str) -> Path:
    target = parent / name
    target.mkdir(parents=False)
    return target


def remember(path: Path) -> tuple[str, VaultModel]:
    resolved = path.resolve()
    folders = [
        VaultFolder(name=VaultFolderName(folder.name), adopted=folder.adopted)
        for folder in layout.ensure(resolved)
    ]
    config = remember_store(resolved)
    identifier = next(
        key for key, entry in config.stores.items() if entry.path == resolved
    )
    return identifier, _as_model(identifier, config.stores[identifier], folders)


def move(identifier: str, source: Path, target: Path) -> VaultModel:
    source.rename(target)
    config = update_store_path(identifier, target)
    return _as_model(identifier, config.stores[identifier], _folders(target))


def forget(identifier: str) -> None:
    """Vault files remain on disk."""
    forget_store(identifier)
