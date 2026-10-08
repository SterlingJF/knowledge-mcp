# File: server/app/config.py
"""Vault-local config directory: `.knowledge-mcp/` (app.vault.layout)."""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from app.utilities.atomic_write import write_atomic
from app.utilities.logging import get_app_logger

logger = get_app_logger("config")

CONFIG_DIRECTORY_NAME = "knowledge-mcp"
CONFIG_FILE_NAME = "config.json"
CONFIG_VERSION = 1


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="ignore"
    )


class FilesystemStore(_CamelModel):
    type: Literal["filesystem"] = "filesystem"
    path: Path
    last_opened: int = 0
    open: bool = False

    @property
    def display_name(self) -> str:
        return self.path.name or str(self.path)


# pdcp-0026 adds another discriminated store type here.
StoreEntry = Annotated[FilesystemStore, Field(discriminator="type")]


class KmConfig(_CamelModel):
    version: int = CONFIG_VERSION
    stores: dict[str, StoreEntry] = Field(default_factory=dict)
    principal_id: str | None = None

    def resolved_store(self) -> FilesystemStore | None:
        if not self.stores:
            return None
        return max(self.stores.values(), key=lambda entry: entry.last_opened)


def config_home() -> Path:
    override = os.environ.get("XDG_CONFIG_HOME")
    base = Path(override).expanduser() if override else Path.home() / ".config"
    return base / CONFIG_DIRECTORY_NAME


def config_path() -> Path:
    return config_home() / CONFIG_FILE_NAME


def new_store_id() -> str:
    return secrets.token_hex(8)


def read_config() -> KmConfig:
    path = config_path()
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return KmConfig()
    except OSError as error:
        logger.warning(
            "Config file could not be read", path=str(path), error=str(error)
        )
        return KmConfig()

    try:
        return KmConfig.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as error:
        logger.warning(
            "Config file is not valid; continuing with no stores",
            path=str(path),
            error=str(error),
        )
        return KmConfig()


def write_config(config: KmConfig) -> None:
    payload = config.model_dump(mode="json", by_alias=True)
    write_atomic(config_path(), json.dumps(payload, indent=2).encode("utf-8") + b"\n")


def _next_opened_at(config: KmConfig) -> int:
    now = time.time_ns() // 1_000_000
    if not config.stores:
        return now
    latest = max(entry.last_opened for entry in config.stores.values())
    return max(now, latest + 1)


def remember_store(path: Path) -> KmConfig:
    config = read_config()
    resolved = Path(path).expanduser().resolve()
    identifier = (
        next(
            (
                existing
                for existing, entry in config.stores.items()
                if entry.path == resolved
            ),
            None,
        )
        or new_store_id()
    )

    config.stores[identifier] = FilesystemStore(
        path=resolved,
        last_opened=_next_opened_at(config),
        open=True,
    )
    write_config(config)
    return config


def update_store_path(identifier: str, path: Path) -> KmConfig:
    config = read_config()
    entry = config.stores.get(identifier)
    if entry is not None:
        entry.path = Path(path).expanduser().resolve()
        write_config(config)
    return config


def forget_store(identifier: str) -> KmConfig:
    config = read_config()
    if config.stores.pop(identifier, None) is not None:
        write_config(config)
    return config


def configured_store_root() -> Path | None:
    entry = read_config().resolved_store()
    return entry.path if entry else None
