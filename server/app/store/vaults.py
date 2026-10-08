# File: server/app/store/vaults.py
from __future__ import annotations

from typing import TYPE_CHECKING

from app.errors import NotFoundError
from app.store.file_store import FileStore
from app.utilities.logging import get_app_logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

logger = get_app_logger("store")

VAULT_HEADER = "X-Km-Vault"


class VaultStores:
    def __init__(
        self,
        default_root: Path | None,
        on_new_root: Callable[[Path], object] | None = None,
    ) -> None:
        self._default_root = default_root
        self._on_new_root = on_new_root
        self._by_root: dict[str, FileStore] = {}

    @property
    def default_root(self) -> Path | None:
        return self._default_root

    def set_default_root(self, root: Path | None) -> None:
        self._default_root = root

    def for_root(self, root: Path | None) -> FileStore:
        key = str(root) if root else ""
        store = self._by_root.get(key)
        if store is None:
            if root is not None:
                self._prepare(root)
            store = FileStore(root)
            self._by_root[key] = store
        return store

    def _prepare(self, root: Path) -> None:
        if self._on_new_root is None:
            return
        try:
            self._on_new_root(root)
        except OSError as error:
            logger.warning(
                "Could not prepare the vault root",
                root=str(root),
                reason=error.strerror,
            )

    def default(self) -> FileStore:
        return self.for_root(self._default_root)

    def forget_root(self, root: Path | None) -> None:
        self._by_root.pop(str(root) if root else "", None)

    def rebind(self, old_root: Path, new_root: Path) -> None:
        self.forget_root(old_root)
        if self._default_root == old_root:
            self._default_root = new_root

    def resolve(self, vault_id: str | None, known: dict[str, Path]) -> FileStore:
        if not vault_id:
            return self.default()
        root = known.get(vault_id)
        if root is None:
            msg = f"No vault with id {vault_id}"
            raise NotFoundError(msg)
        return self.for_root(root)
