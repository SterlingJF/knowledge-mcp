# File: mcp/tests/conftest.py
"""No real backend calls."""

from __future__ import annotations

from typing import Any

import pytest

from app import km_api
from app.settings import AGENT_PARTY, load_settings

AGENT = AGENT_PARTY
UNIVERSE_ID = 'product-development'
UNIVERSE_VERSION = '0.5'
DECISION_RECORD = 'ayx0k'
DECISION = 'e43c2'


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def configured(settings):
    km_api.configure(settings)
    return settings


class Recorder:
    def __init__(self, answers: list[Any]) -> None:
        self.answers = list(answers)
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        vault: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        self.calls.append(
            {
                'method': method,
                'path': path,
                'params': params,
                'json': json,
                'vault': vault,
                'headers': headers,
            }
        )
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer, {
            'method': method,
            'url': path,
            'status': 200,
            'elapsedMs': 1.0,
            'etag': '"etag"',
        }


@pytest.fixture
def seam(monkeypatch):
    def install(*answers: Any) -> Recorder:
        recorder = Recorder(list(answers))
        monkeypatch.setattr(km_api, 'request', recorder)
        return recorder

    return install


@pytest.fixture
def tools():
    registry: dict[str, Any] = {}

    class Collector:
        def tool(self, **kwargs: Any):
            def decorate(function):
                registry[kwargs['name']] = function
                return function

            return decorate

    from app.tools import artifacts, files, universes, vaults

    collector = Collector()
    artifacts.register(collector)
    files.register(collector)
    universes.register(collector)
    vaults.register(collector)
    return registry
