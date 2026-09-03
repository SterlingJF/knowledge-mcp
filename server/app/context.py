# File: server/app/context.py
"""Agent claims from `X-Km-Agent` are unverified. Invalid or absent claims use local principal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated

import structlog
from fastapi import Depends, Header, Request

AGENT_HEADER = 'X-Km-Agent'
PERSON_PREFIX = 'local-principal:'
AGENT_PREFIX = 'agent:'

AGENT_NAME = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')


@dataclass(frozen=True, slots=True)
class RequestContext:
    actor: str
    is_agent: bool

    @property
    def party(self) -> str:
        """Party value stamped into `createdBy` (app.store.service.ArtifactService.create)."""
        return self.actor


def _person(principal_id: str) -> RequestContext:
    return RequestContext(actor=f'{PERSON_PREFIX}{principal_id}', is_agent=False)


def _agent(name: str) -> RequestContext:
    return RequestContext(actor=f'{AGENT_PREFIX}{name}', is_agent=True)


def resolve_context(request: Request, agent_header: str | None) -> RequestContext:
    settings = request.app.state.settings
    if agent_header is None:
        return _person(settings.PRINCIPAL_ID)

    candidate = agent_header.strip().lower()
    if not AGENT_NAME.match(candidate):
        structlog.contextvars.bind_contextvars(agent_header_rejected=agent_header[:80])
        return _person(settings.PRINCIPAL_ID)
    return _agent(candidate)


async def get_request_context(
    request: Request,
    x_km_agent: Annotated[str | None, Header(alias=AGENT_HEADER)] = None,
) -> RequestContext:
    context = resolve_context(request, x_km_agent)
    structlog.contextvars.bind_contextvars(actor=context.actor)
    return context


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
