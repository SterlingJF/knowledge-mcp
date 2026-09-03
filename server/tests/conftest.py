# File: server/tests/conftest.py
"""Fixtures using bundled universes."""

from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from app.factory import create_app
from app.settings import load_settings

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

PERSON = 'local-principal:tester'
AGENT = 'agent:knowledge-mcp-structure'
AGENT_HEADERS = {'X-Km-Agent': 'knowledge-mcp-structure'}

UNIVERSE = {'id': 'product-development', 'version': '0.5'}
DECISION_RECORD = 'ayx0k'
DECISION = 'e43c2'
REVERSAL_CONDITION = 'ebxtg'
UNCLOSABLE = 'egp69'


@pytest.fixture(autouse=True)
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every test at its own config home. Config file is a settings source."""
    home = tmp_path / 'config-home'
    home.mkdir()
    monkeypatch.setenv('XDG_CONFIG_HOME', str(home))
    return home / 'knowledge-mcp'


@pytest.fixture
def store_root(tmp_path: Path) -> Path:
    root = tmp_path / 'vault'
    root.mkdir()
    return root


@pytest.fixture
def client(store_root: Path) -> Iterator[TestClient]:
    settings = load_settings(
        ROLE='desktop',
        STORE_ROOT=store_root,
        PRINCIPAL_ID='tester',
        LOG_LEVEL='WARNING',
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


_written = count(1)


def creation_payload(**overrides: Any) -> dict[str, Any]:
    """Minimal valid create payload asserted by the person."""
    payload: dict[str, Any] = {
        'universe': dict(UNIVERSE),
        'artifactType': DECISION_RECORD,
        'name': 'Storage backend for the local-first MVP',
        'path': f'Efforts/artifact-{next(_written)}.md',
        'projectId': None,
        'data': {
            DECISION: [
                {
                    'element': DECISION,
                    'value': 'Files, not a database.',
                    'asserted_by': PERSON,
                    'status': 'contracted',
                }
            ]
        },
    }
    payload.update(overrides)
    return payload


def create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post('/api/v1/artifacts', json=creation_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()
