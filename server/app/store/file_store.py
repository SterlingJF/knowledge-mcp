# File: server/app/store/file_store.py
"""ETag recheck detects stale content before rename. Hash check and rename are not isolated."""

from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.api_models_auto import VaultFolderName
from app.errors import (
    ConflictError,
    NotFoundError,
    StoreUnavailableError,
    UnusablePathError,
)
from app.store import codec
from app.utilities.atomic_write import TEMP_PREFIX, write_atomic
from app.utilities.logging import get_app_logger

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = get_app_logger("store")

SKIPPED_DIRECTORIES = frozenset(
    {"node_modules", ".git", ".obsidian", ".knowledge-mcp", ".trash", "__pycache__"}
)

CONTENT_FOLDERS: tuple[str, ...] = tuple(
    folder.value for folder in VaultFolderName if not folder.value.startswith(".")
)


@dataclass(slots=True)
class StoredArtifact:
    artifact: dict[str, Any]
    prose_keys: dict[str, str]
    coercions: list[codec.Coercion]
    path: Path
    etag: str


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: Path
    relative_path: str
    size: int
    modified_at: datetime


@dataclass(slots=True)
class _CacheEntry:
    signature: tuple[int, int]
    stored: StoredArtifact


class FileStore:
    def __init__(self, root: Path | None) -> None:
        self._root = Path(root).expanduser() if root else None
        self._cache: dict[Path, _CacheEntry] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @property
    def root(self) -> Path | None:
        return self._root

    def is_ready(self) -> tuple[bool, str | None]:
        if self._root is None:
            return False, "No storage root is configured"
        if not self._root.exists():
            return False, f"Storage root does not exist: {self._root}"
        if not self._root.is_dir():
            return False, f"Storage root is not a directory: {self._root}"
        if not os.access(self._root, os.R_OK | os.W_OK):
            return False, f"Storage root is not readable and writable: {self._root}"
        return True, None

    def _require_root(self) -> Path:
        ready, reason = self.is_ready()
        if not ready or self._root is None:
            raise StoreUnavailableError(reason or "Storage root unavailable")
        return self._root

    def lock_for(self, artifact_id: str) -> asyncio.Lock:
        return self._locks[artifact_id]

    def _directory_identity(self, directory: Path) -> tuple[int, int] | None:
        try:
            directory_stat = directory.stat()
        except OSError:
            return None
        return directory_stat.st_dev, directory_stat.st_ino

    def _directory_entries(self, directory: Path) -> list[os.DirEntry[str]]:
        try:
            with os.scandir(directory) as iterator:
                return sorted(iterator, key=lambda entry: entry.name)
        except OSError:
            return []

    def _walk_entry(
        self,
        directory: Path,
        entry: os.DirEntry[str],
        ancestors: frozenset[tuple[int, int]],
    ) -> Iterator[Path]:
        path = directory / entry.name
        try:
            if entry.is_dir(follow_symlinks=True):
                if (
                    not entry.name.startswith(".")
                    and entry.name not in SKIPPED_DIRECTORIES
                ):
                    yield from self._walk_directory(path, ancestors)
                return
            if entry.is_file(follow_symlinks=True):
                if not entry.name.startswith(TEMP_PREFIX):
                    yield path
                return
        except OSError:
            pass
        if entry.is_symlink() and not entry.name.startswith(TEMP_PREFIX):
            yield path

    def _walk_directory(
        self,
        directory: Path,
        ancestors: frozenset[tuple[int, int]],
    ) -> Iterator[Path]:
        identity = self._directory_identity(directory)
        if identity is None or identity in ancestors:
            return

        descendants = ancestors | {identity}
        for entry in self._directory_entries(directory):
            yield from self._walk_entry(directory, entry, descendants)

    def _walk(self, root: Path) -> Iterator[Path]:
        for folder in CONTENT_FOLDERS:
            content_root = root / folder
            yield from self._walk_directory(content_root, frozenset())

    def files(self) -> list[StoredFile]:
        root = self._require_root().absolute()
        results: list[StoredFile] = []
        for path in sorted(self._walk(root)):
            try:
                file_stat = path.stat()
            except OSError:
                try:
                    file_stat = path.lstat()
                except OSError:
                    continue
                if not path.is_symlink():
                    continue
            results.append(
                StoredFile(
                    path=path,
                    relative_path=path.relative_to(root).as_posix(),
                    size=file_stat.st_size,
                    modified_at=datetime.fromtimestamp(file_stat.st_mtime, UTC),
                )
            )
        return results

    def read_file(self, vault_path: str) -> tuple[StoredFile, str | None]:
        for stored in self.files():
            if stored.relative_path != vault_path:
                continue
            if not stored.path.name.endswith(".md"):
                return stored, None
            try:
                return stored, stored.path.read_text(encoding="utf-8")
            except OSError, UnicodeDecodeError:
                return stored, None
        msg = f"No vault file at {vault_path}"
        raise NotFoundError(msg)

    def _load(self, path: Path) -> StoredArtifact | None:
        try:
            stat = path.stat()
        except OSError:
            self._cache.pop(path, None)
            return None

        signature = (stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(path)
        if cached is not None and cached.signature == signature:
            return cached.stored

        try:
            raw = path.read_bytes()
            artifact, prose_keys, coercions = codec.from_bytes(raw)
        except Exception as error:  # a broken file must not crash the scan
            logger.warning(
                "Skipping unparseable file", path=str(path), error=str(error)
            )
            self._cache.pop(path, None)
            return None

        if not artifact.get("id"):
            logger.warning("Skipping file with no artifact id", path=str(path))
            self._cache.pop(path, None)
            return None

        stored = StoredArtifact(
            artifact=artifact,
            prose_keys=prose_keys,
            coercions=coercions,
            path=path,
            etag=codec.compute_etag(raw),
        )
        self._cache[path] = _CacheEntry(signature=signature, stored=stored)
        return stored

    def scan(self) -> list[StoredArtifact]:
        """First sorted path wins duplicate ids."""
        root = self._require_root()
        seen: dict[str, StoredArtifact] = {}
        for path in sorted(
            path for path in self._walk(root) if path.name.endswith(".md")
        ):
            stored = self._load(path)
            if stored is None:
                continue
            artifact_id = str(stored.artifact["id"])
            if artifact_id in seen:
                logger.warning(
                    "Duplicate artifact id on disk; the first path wins",
                    artifact_id=artifact_id,
                    kept=str(seen[artifact_id].path),
                    ignored=str(path),
                )
                continue
            seen[artifact_id] = stored
        return list(seen.values())

    def get(self, artifact_id: str) -> StoredArtifact:
        for stored in self.scan():
            if str(stored.artifact["id"]) == artifact_id:
                return stored
        msg = f"No artifact with id {artifact_id}"
        raise NotFoundError(msg)

    def find(self, artifact_id: str) -> StoredArtifact | None:
        try:
            return self.get(artifact_id)
        except NotFoundError, StoreUnavailableError:
            return None

    def resolve_new(self, vault_path: str) -> Path:
        root = self._require_root().absolute()
        relative = Path(vault_path)

        if relative.is_absolute() or ".." in relative.parts:
            msg = f"That path leaves the vault: {vault_path}"
            raise UnusablePathError(msg)

        parts = relative.parts
        if not parts or parts[0] not in CONTENT_FOLDERS:
            declared = ", ".join(CONTENT_FOLDERS)
            msg = f"A path has to start with one of {declared}: {vault_path}"
            raise UnusablePathError(msg)

        candidate = root / relative
        if candidate.exists() or candidate.is_symlink():
            msg = f"Something is already at that path: {vault_path}"
            raise ConflictError(msg)

        return candidate

    def write(
        self,
        artifact: dict[str, Any],
        prose_keys: dict[str, str],
        path: Path,
        expected_etag: str | None = None,
    ) -> StoredArtifact:
        self._require_root()
        raw = codec.to_bytes(artifact, prose_keys)

        if expected_etag is not None and path.exists():
            current = codec.compute_etag(path.read_bytes())
            if current != expected_etag:
                msg = (
                    "The file changed between read and write; re-read it and try again"
                )
                raise ConflictError(
                    msg,
                    fields={
                        "path": path.name,
                        "expectedEtag": expected_etag,
                        "actualEtag": current,
                    },
                )

        write_path = path.resolve() if path.is_symlink() else path
        write_atomic(write_path, raw)
        self._cache.pop(path, None)
        self._cache.pop(write_path, None)
        stored = self._load(path)
        if stored is None:  # pragma: no cover - post-write invariant
            msg = "The artifact could not be re-read after writing"
            raise ConflictError(msg)
        return stored

    def delete(self, path: Path) -> None:
        self._require_root()
        try:
            path.unlink()
        except FileNotFoundError as error:
            msg = "The artifact file is already gone"
            raise NotFoundError(msg) from error
        self._cache.pop(path, None)
