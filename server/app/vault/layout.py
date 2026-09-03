# File: server/app/vault/layout.py
from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from app.api_models_auto import VaultFolderName

if TYPE_CHECKING:
    from pathlib import Path

VAULT_FOLDERS: tuple[str, ...] = tuple(folder.value for folder in VaultFolderName)

CONFIG_FOLDER = '.knowledge-mcp'

CONTENT_FOLDERS: tuple[str, ...] = tuple(
    name for name in VAULT_FOLDERS if name != CONFIG_FOLDER
)


class VaultFolderState(NamedTuple):
    name: str
    adopted: bool


def inspect(root: Path) -> list[VaultFolderState]:
    return [
        VaultFolderState(name=name, adopted=(root / name).is_dir())
        for name in VAULT_FOLDERS
    ]


def ensure(root: Path) -> list[VaultFolderState]:
    state = inspect(root)
    for folder in state:
        if not folder.adopted:
            (root / folder.name).mkdir(parents=True, exist_ok=True)
    return state
