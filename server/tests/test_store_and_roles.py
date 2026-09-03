# File: server/tests/test_store_and_roles.py

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

import pytest

from app.errors import ConflictError
from app.store import codec
from app.store.file_store import FileStore
from app.utilities.atomic_write import write_atomic
from tests.conftest import DECISION, create, creation_payload

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_an_artifact_moved_into_a_subfolder_is_still_found(
    client: TestClient, store_root: Path
):
    artifact = create(client)
    path = next(store_root.rglob('*.md'))
    nested = store_root / 'Efforts' / 'Knowledge Bus Protocol'
    nested.mkdir(parents=True)
    path.rename(nested / path.name)

    assert client.get(f'/api/v1/artifacts/{artifact["id"]}').status_code == 200


def test_an_artifact_beyond_six_folders_is_still_found(client: TestClient):
    artifact = create(
        client,
        path='Efforts/one/two/three/four/five/six/seven/eight/artifact.md',
    )

    assert client.get(f'/api/v1/artifacts/{artifact["id"]}').status_code == 200


def test_a_symlinked_artifact_can_be_read_updated_and_unlinked(
    client: TestClient, store_root: Path, tmp_path: Path
):
    artifact = create(client)
    alias = next((store_root / 'Efforts').glob('artifact-*.md'))
    target = tmp_path / 'linked-artifact.md'
    alias.rename(target)
    alias.symlink_to(target)

    fetched = client.get(f'/api/v1/artifacts/{artifact["id"]}')
    updated = client.put(
        f'/api/v1/artifacts/{artifact["id"]}',
        json={'name': 'A decision record reached through a symlink'},
        headers={'If-Match': fetched.headers['ETag']},
    )

    assert updated.status_code == 200
    assert alias.is_symlink()
    assert 'A decision record reached through a symlink' in target.read_text()

    assert client.delete(f'/api/v1/artifacts/{artifact["id"]}').status_code == 204
    assert not alias.exists()
    assert target.exists()


def test_an_artifact_can_be_created_beneath_a_symlinked_directory(
    client: TestClient, store_root: Path, tmp_path: Path
):
    target = tmp_path / 'external-effort'
    target.mkdir()
    (store_root / 'Efforts' / 'linked').symlink_to(target, target_is_directory=True)

    artifact = create(client, path='Efforts/linked/artifact.md')

    assert (target / 'artifact.md').exists()
    assert client.get(f'/api/v1/artifacts/{artifact["id"]}').status_code == 200


def test_a_renamed_file_is_still_found_by_id(client: TestClient, store_root: Path):
    artifact = create(client)
    path = next(store_root.rglob('*.md'))
    path.rename(path.parent / 'something-a-person-typed.md')

    body = client.get(f'/api/v1/artifacts/{artifact["id"]}').json()
    assert body['name'] == 'Storage backend for the local-first MVP'


def test_a_broken_file_does_not_take_the_listing_down(
    client: TestClient, store_root: Path
):
    create(client)
    (store_root / 'broken.md').write_text('---\nthis: [is not: valid yaml\n---\n')

    response = client.get('/api/v1/artifacts')
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_dot_directories_are_skipped(client: TestClient, store_root: Path):
    create(client)
    hidden = store_root / '.obsidian' / 'plugins'
    hidden.mkdir(parents=True)
    source = next(store_root.rglob('*.md'))
    (hidden / 'copy.md').write_bytes(source.read_bytes())

    assert len(client.get('/api/v1/artifacts').json()) == 1


def test_atomic_write_leaves_the_original_intact_on_failure(
    store_root: Path, monkeypatch
):
    target = store_root / 'artifact.md'
    target.write_bytes(b'original')

    def explode(*_args: object, **_kwargs: object) -> None:
        msg = 'disk gave up'
        raise OSError(msg)

    monkeypatch.setattr('app.utilities.atomic_write.os.replace', explode)
    with pytest.raises(OSError, match='disk gave up'):
        write_atomic(target, b'replacement')

    assert target.read_bytes() == b'original'
    assert list(store_root.glob('.knowledge-mcp-*')) == []


def test_a_write_against_a_stale_etag_is_refused(store_root: Path):
    store = FileStore(store_root)
    artifact = {
        'id': '11111111-1111-4111-8111-111111111111',
        'name': 'A name long enough',
    }
    path = store_root / 'artifact.md'
    stored = store.write(artifact, {}, path)

    path.write_bytes(path.read_bytes() + b'\nedited by a person\n')

    with pytest.raises(ConflictError):
        store.write(artifact, {}, path, expected_etag=stored.etag)


def test_the_hash_is_never_written_into_the_file(store_root: Path):
    store = FileStore(store_root)
    stored = store.write(
        {'id': '11111111-1111-4111-8111-111111111111', 'name': 'A name long enough'},
        {},
        store_root / 'artifact.md',
    )

    assert 'sha256' not in stored.path.read_text()
    assert stored.etag == codec.compute_etag(stored.path.read_bytes())


def test_lists_the_bundled_universe_with_a_string_version(client: TestClient):
    body = client.get('/api/v1/universes').json()
    by_id = {universe['id']: universe for universe in body}

    assert set(by_id) == {'product-development'}
    assert by_id['product-development']['version'] == '0.5'


def test_guidance_resolves_or_404s(client: TestClient):
    assert (
        client.get('/api/v1/universes/product-development/guidance').status_code == 200
    )
    assert client.get('/api/v1/universes/not-a-universe/guidance').status_code == 404
    assert client.get('/api/v1/universes/not-a-universe').status_code == 404


def test_the_desktop_role_serves_artifacts_and_universes(client: TestClient):
    assert client.get('/api/v1/artifacts').status_code == 200
    assert client.get('/api/v1/universes').status_code == 200


def test_a_hosted_only_path_is_not_mounted(client: TestClient):
    assert client.get('/api/v1/organizations').status_code == 404
    assert client.get('/api/v1/users/me').status_code == 404


def test_health_and_ready(client: TestClient):
    assert client.get('/health').json()['status'] == 'healthy'

    ready = client.get('/ready').json()
    assert ready['status'] == 'ready'
    assert ready['universesLoaded'] == 1
    assert ready['storageReady'] is True


def test_ready_reports_not_ready_without_a_storage_root(tmp_path: Path):
    from fastapi.testclient import TestClient as Client

    from app.factory import create_app
    from app.settings import load_settings

    with Client(
        create_app(load_settings(ROLE='desktop', LOG_LEVEL='WARNING'))
    ) as client:
        response = client.get('/ready')

    assert response.status_code == 503
    assert response.json()['storageReady'] is False


def test_a_missing_storage_root_is_a_503_not_a_crash(tmp_path: Path):
    from fastapi.testclient import TestClient as Client

    from app.factory import create_app
    from app.settings import load_settings

    with Client(
        create_app(load_settings(ROLE='desktop', LOG_LEVEL='WARNING'))
    ) as client:
        response = client.get('/api/v1/artifacts')

    assert response.status_code == 503
    assert response.json()['errorCode'] == 'STORE_UNAVAILABLE'


def test_cors_exposes_the_etag_to_a_desktop_origin(client: TestClient):
    response = client.get('/api/v1/artifacts', headers={'Origin': 'tauri://localhost'})

    exposed = response.headers['access-control-expose-headers']
    assert 'ETag' in exposed
    assert response.headers['access-control-allow-origin'] == 'tauri://localhost'


def test_cors_preflight_allows_the_agent_header(client: TestClient):
    response = client.options(
        '/api/v1/artifacts',
        headers={
            'Origin': 'tauri://localhost',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'X-Km-Agent',
        },
    )

    assert response.status_code == 200
    assert 'x-km-agent' in response.headers['access-control-allow-headers'].lower()


def test_every_response_carries_a_request_id(client: TestClient):
    assert client.get('/health').headers['X-Request-ID']


class TestTheCallerNamesTheLocation:
    def test_an_artifact_lands_exactly_where_it_was_asked_to(
        self, client: TestClient, store_root: Path
    ) -> None:
        created = create(client, path='Efforts/Local-First MVP/decisions/chosen.md')

        written = store_root / 'Efforts' / 'Local-First MVP' / 'decisions' / 'chosen.md'
        assert written.is_file()
        assert client.get(f'/api/v1/artifacts/{created["id"]}').status_code == 200

    def test_a_path_outside_the_declared_folders_is_refused(
        self, client: TestClient, store_root: Path
    ) -> None:
        answered = client.post(
            '/api/v1/artifacts', json=creation_payload(path='Scratch/note.md')
        )

        assert answered.status_code == 422
        assert 'has to start with one of' in answered.json()['detail']
        assert not (store_root / 'Scratch').exists()

    def test_the_config_folder_is_not_content(self, client: TestClient) -> None:
        answered = client.post(
            '/api/v1/artifacts', json=creation_payload(path='.knowledge-mcp/sneaky.md')
        )

        assert answered.status_code == 422

    def test_a_path_escaping_the_vault_is_refused(
        self, client: TestClient, store_root: Path
    ) -> None:
        answered = client.post(
            '/api/v1/artifacts',
            json=creation_payload(path='Efforts/../../outside.md'),
        )

        assert answered.status_code == 422
        assert not (store_root.parent / 'outside.md').exists()

    def test_a_taken_path_is_refused_rather_than_renamed(
        self, client: TestClient, store_root: Path
    ) -> None:
        create(client, path='Efforts/taken.md')

        answered = client.post(
            '/api/v1/artifacts', json=creation_payload(path='Efforts/taken.md')
        )

        assert answered.status_code == 409
        assert [p.name for p in (store_root / 'Efforts').glob('taken*.md')] == [
            'taken.md'
        ]
