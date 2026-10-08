# File: mcp-server/app/settings.py
"""No secrets. Every setting has a working default."""

from __future__ import annotations

import re

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sole accepted revision (app.front_door.FrontDoor).
MCP_REVISION = "2026-07-28"

# _meta keys defined by 2026-07-28 revision.
META_PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES_KEY = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT_INFO_KEY = "io.modelcontextprotocol/clientInfo"

# `just check_ports` checks this against the other copies of the port.
DEFAULT_PORT = 17952

DEFAULT_API_ORIGIN = "http://127.0.0.1:17951/api/v1"

# Malformed agent name resolves to the person (server/app/context.py).
AGENT_NAME = "knowledge-mcp"

# From `X-Km-Agent` in contracts/project/v1.
AGENT_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

# Agent `asserted_by` value (`contracts/extensions/knowledge-bus/upstream/Knowledge Bus Protocol (KBP).yaml`).
AGENT_PARTY = f"agent:{AGENT_NAME}"

if not AGENT_NAME_PATTERN.match(AGENT_NAME):
    _msg = (
        f"AGENT_NAME {AGENT_NAME!r} does not match the contract pattern "
        f"{AGENT_NAME_PATTERN.pattern}. The backend would read it as no claim at all and record "
        f"every write as the person, which is the opposite of what this server is for."
    )
    raise ValueError(_msg)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KM_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        frozen=True,
        extra="ignore",
    )

    APP_NAME: str = "knowledge-mcp"

    HOST: str = "127.0.0.1"
    PORT: int = DEFAULT_PORT

    API_ORIGIN: str = DEFAULT_API_ORIGIN

    # Local reads scan the folder (server/app/store/file_store.py).
    API_TIMEOUT_SECONDS: float = 30.0

    LOG_LEVEL: str = "WARNING"

    @field_validator("API_ORIGIN")
    @classmethod
    def _api_origin_is_absolute(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned.startswith(("http://", "https://")):
            msg = (
                f"KM_MCP_API_ORIGIN must be an absolute http(s) origin, got {value!r}. "
                f"Example: {DEFAULT_API_ORIGIN}"
            )
            raise ValueError(msg)
        return cleaned


def load_settings(**overrides: object) -> Settings:
    supplied = {key: value for key, value in overrides.items() if value is not None}
    return Settings(**supplied)  # type: ignore[arg-type]
