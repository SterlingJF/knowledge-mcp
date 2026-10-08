# File: server/app/settings.py
from __future__ import annotations

import getpass
from pathlib import (
    Path,  # Pydantic resolves this field type at runtime
)
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from app.config import read_config

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

Role = Literal["desktop"]

DESKTOP_ORIGINS: tuple[str, ...] = (
    "tauri://localhost",
    "http://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)

# ETag is not a CORS-safelisted response header.
EXPOSED_HEADERS: tuple[str, ...] = ("ETag", "X-Request-ID")

ALLOWED_HEADERS: tuple[str, ...] = (
    "Authorization",
    "Content-Type",
    "If-Match",
    "X-Current-Org-Id",
    "X-Km-Agent",
    "X-Km-Client",
    "X-Km-Vault",
    "X-Request-ID",
)


class KmConfigSource(PydanticBaseSettingsSource):
    def get_field_value(
        self,
        field: FieldInfo,  # field resolution occurs in `__call__`
        field_name: str,
    ) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        config = read_config()
        values: dict[str, Any] = {}

        entry = config.resolved_store()
        if entry is not None:
            values["STORE_ROOT"] = entry.path
        if config.principal_id:
            values["PRINCIPAL_ID"] = config.principal_id

        return values


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KM_",
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )

    APP_NAME: str = "km-server"
    ENVIRONMENT: str = "local"
    ROLE: Role = "desktop"

    API_PREFIX: str = "/api/v1"
    HOST: str | None = None
    PORT: int = 8000

    STORE_ROOT: Path | None = None
    # Bundled-universe override (app.knowledge_model).
    KNOWLEDGE_MODEL_DIR: Path | None = None

    # Principal minting is unimplemented.
    PRINCIPAL_ID: str = Field(default_factory=getpass.getuser)

    CORS_ORIGINS: tuple[str, ...] = DESKTOP_ORIGINS

    LOG_LEVEL: str = "INFO"
    FORCE_JSON_LOGS: bool = False

    HEALTH_PATHS: frozenset[str] = frozenset({"/health", "/ready", "/"})
    LOW_NOISE_PATHS: frozenset[str] = frozenset({"/health", "/ready"})

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            KmConfigSource(settings_cls),
            file_secret_settings,
        )

    @field_validator("PRINCIPAL_ID")
    @classmethod
    def _principal_id_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            msg = "KM_PRINCIPAL_ID must not be blank"
            raise ValueError(msg)
        return value.strip()

    @property
    def bind_host(self) -> str:
        if self.HOST:
            return self.HOST
        return "127.0.0.1" if self.ROLE == "desktop" else "0.0.0.0"

    @property
    def cors_origins(self) -> list[str]:
        return list(self.CORS_ORIGINS)


def load_settings(**overrides: object) -> Settings:
    supplied = {key: value for key, value in overrides.items() if value is not None}
    return Settings(**supplied)  # type: ignore[arg-type]
