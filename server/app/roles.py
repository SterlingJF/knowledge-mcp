# File: server/app/roles.py
from __future__ import annotations

from typing import TYPE_CHECKING

from app.routers import artifacts, files, health, storage, universes, vaults

if TYPE_CHECKING:
    from fastapi import APIRouter

    from app.settings import Role

API_ROUTERS: dict[str, list[APIRouter]] = {
    "desktop": [artifacts.router, files.router, universes.router, vaults.router],
}

ROOT_ROUTERS: list[APIRouter] = [health.router]

# Desktop storage routes are absent from `contracts/project/v1/vault.rest.openapi.yaml`.
ROLE_ROOT_ROUTERS: dict[str, list[APIRouter]] = {
    "desktop": [storage.router],
}


def api_routers_for(role: Role) -> list[APIRouter]:
    return API_ROUTERS.get(role, [])


def root_routers_for(role: Role) -> list[APIRouter]:
    return [*ROOT_ROUTERS, *ROLE_ROOT_ROUTERS.get(role, [])]
