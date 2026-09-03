# File: server/tests/test_config_and_storage.py

from __future__ import annotations

import errno
import json
import os
import re
import shutil
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from app import config as app_config
from app.factory import create_app
from app.routers import storage as storage_router
from app.settings import Settings, load_settings
from app.store.file_store import FileStore
from app.vault import service as vault_service
from tests.conftest import create, creation_payload

if TYPE_CHECKING:
    from pathlib import Path

NOT_ROOT = pytest.mark.skipif(
    hasattr(os, 'geteuid') and os.geteuid() == 0,
    reason='Permission bits do not restrain root',
)


def write_config_file(config_home: Path, payload: dict[str, object]) -> Path:
    config_home.mkdir(parents=True, exist_ok=True)
    path = config_home / 'config.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path


def store_payload(path: Path, **overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        'type': 'filesystem',
        'path': str(path),
        'lastOpened': 1,
        'open': True,
    }
    entry.update(overrides)
    return {'version': 1, 'stores': {'abc123': entry}}


class TestConfigFile:
    def test_an_absent_file_is_an_empty_config(self, config_home: Path) -> None:
        assert not (config_home / 'config.json').exists()
        assert app_config.read_config().stores == {}

    def test_malformed_json_is_an_empty_config(self, config_home: Path) -> None:
        config_home.mkdir(parents=True)
        (config_home / 'config.json').write_text('{ not json', encoding='utf-8')
        assert app_config.read_config().stores == {}

    def test_an_unrecognised_shape_is_an_empty_config(self, config_home: Path) -> None:
        write_config_file(config_home, {'version': 1, 'stores': 'not-a-mapping'})
        assert app_config.read_config().stores == {}

    def test_remembering_a_store_round_trips(
        self, config_home: Path, store_root: Path
    ) -> None:
        app_config.remember_store(store_root)

        reread = app_config.read_config()
        entry = reread.resolved_store()
        assert entry is not None
        assert entry.path == store_root.resolve()
        assert entry.open is True
        assert entry.last_opened > 0
        assert json.loads((config_home / 'config.json').read_text())['version'] == 1

    def test_remembering_the_same_folder_twice_keeps_one_entry(
        self, store_root: Path
    ) -> None:
        app_config.remember_store(store_root)
        app_config.remember_store(store_root)
        assert len(app_config.read_config().stores) == 1

    def test_opening_a_store_does_not_close_the_others(
        self, tmp_path: Path, store_root: Path
    ) -> None:
        other = tmp_path / 'other-vault'
        other.mkdir()

        app_config.remember_store(store_root)
        app_config.remember_store(other)

        stores = app_config.read_config().stores
        assert all(entry.open for entry in stores.values())
        # Recency picks default (KmConfig.resolved_store).
        assert app_config.read_config().resolved_store().path == other.resolve()

    def test_vaults_opened_in_the_same_millisecond_still_order(
        self, tmp_path: Path, store_root: Path
    ) -> None:
        other = tmp_path / 'other-vault'
        other.mkdir()

        app_config.remember_store(store_root)
        app_config.remember_store(other)

        stamps = [
            entry.last_opened for entry in app_config.read_config().stores.values()
        ]
        assert len(set(stamps)) == len(stamps)

    def test_a_store_is_named_after_its_folder(self, store_root: Path) -> None:
        app_config.remember_store(store_root)
        entry = app_config.read_config().resolved_store()
        assert entry is not None
        assert entry.display_name == store_root.name

    def test_the_most_recent_wins_when_nothing_is_open(
        self, config_home: Path, tmp_path: Path
    ) -> None:
        older, newer = tmp_path / 'older', tmp_path / 'newer'
        older.mkdir()
        newer.mkdir()
        write_config_file(
            config_home,
            {
                'version': 1,
                'stores': {
                    'a': {'type': 'filesystem', 'path': str(older), 'lastOpened': 10},
                    'b': {'type': 'filesystem', 'path': str(newer), 'lastOpened': 20},
                },
            },
        )
        assert app_config.read_config().resolved_store().path == newer


class TestResolutionOrder:
    """Command-line flag, then environment, then config file, then default."""

    def test_the_config_file_supplies_the_store_root(
        self, config_home: Path, store_root: Path
    ) -> None:
        write_config_file(config_home, store_payload(store_root))
        assert store_root == Settings().STORE_ROOT

    def test_the_environment_beats_the_config_file(
        self,
        config_home: Path,
        store_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from_env = tmp_path / 'from-env'
        from_env.mkdir()
        write_config_file(config_home, store_payload(store_root))
        monkeypatch.setenv('KM_STORE_ROOT', str(from_env))

        assert from_env == Settings().STORE_ROOT

    def test_a_command_line_flag_beats_the_environment(
        self,
        config_home: Path,
        store_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from_env, from_flag = tmp_path / 'from-env', tmp_path / 'from-flag'
        from_env.mkdir()
        from_flag.mkdir()
        write_config_file(config_home, store_payload(store_root))
        monkeypatch.setenv('KM_STORE_ROOT', str(from_env))

        assert from_flag == load_settings(STORE_ROOT=from_flag).STORE_ROOT

    def test_no_store_anywhere_leaves_the_root_unset(self) -> None:
        assert Settings().STORE_ROOT is None

    def test_the_config_file_supplies_the_principal_id(
        self, config_home: Path, store_root: Path
    ) -> None:
        payload = store_payload(store_root)
        payload['principalId'] = 'sterling'
        write_config_file(config_home, payload)

        assert Settings().PRINCIPAL_ID == 'sterling'

    def test_the_environment_beats_the_config_file_for_principal_id(
        self, config_home: Path, store_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = store_payload(store_root)
        payload['principalId'] = 'from-config'
        write_config_file(config_home, payload)
        monkeypatch.setenv('KM_PRINCIPAL_ID', 'from-env')

        assert Settings().PRINCIPAL_ID == 'from-env'

    def test_a_principal_id_falls_back_to_the_os_login_name(self) -> None:
        assert Settings().PRINCIPAL_ID


class TestStorageRoute:
    def test_get_reports_the_current_store(
        self, client: TestClient, store_root: Path
    ) -> None:
        body = client.get('/storage').json()

        assert body['storageRoot'] == str(store_root)
        assert body['storageName'] == store_root.name
        assert body['storageReady'] is True
        assert [option['type'] for option in body['options']] == ['filesystem']

    def test_putting_a_folder_applies_and_remembers_it(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        chosen = tmp_path / 'chosen'
        chosen.mkdir()

        response = client.put('/storage', json={'path': str(chosen)})

        assert response.status_code == 200, response.text
        assert response.json()['storageRoot'] == str(chosen.resolve())
        assert response.json()['storageReady'] is True
        assert app_config.configured_store_root() == chosen.resolve()

    def test_the_change_is_visible_without_a_restart(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        chosen = tmp_path / 'chosen'
        chosen.mkdir()

        client.put('/storage', json={'path': str(chosen)})

        assert client.get('/ready').json()['storageRoot'] == str(chosen.resolve())

    def test_a_missing_folder_is_refused_and_not_remembered(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        missing = tmp_path / 'not-there'

        response = client.put('/storage', json={'path': str(missing)})

        assert response.status_code == 422
        assert response.json()['storageDetail'] == (
            f'Storage root does not exist: {missing}'
        )
        assert app_config.configured_store_root() is None

    def test_a_file_is_refused(self, client: TestClient, tmp_path: Path) -> None:
        not_a_directory = tmp_path / 'notes.md'
        not_a_directory.write_text('hello', encoding='utf-8')

        response = client.put('/storage', json={'path': str(not_a_directory)})

        assert response.status_code == 422
        assert 'not a directory' in response.json()['storageDetail']

    @NOT_ROOT
    def test_an_unwritable_folder_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        locked = tmp_path / 'locked'
        locked.mkdir()
        locked.chmod(0o500)
        try:
            response = client.put('/storage', json={'path': str(locked)})
        finally:
            locked.chmod(0o700)

        assert response.status_code == 422
        assert 'readable and writable' in response.json()['storageDetail']

    def test_a_refusal_leaves_the_running_store_alone(
        self, client: TestClient, store_root: Path, tmp_path: Path
    ) -> None:
        client.put('/storage', json={'path': str(tmp_path / 'not-there')})

        assert client.get('/ready').json()['storageRoot'] == str(store_root)

    def test_a_refusal_carries_the_same_keys_as_a_success(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        succeeded = client.get('/storage')
        refused = client.put('/storage', json={'path': str(tmp_path / 'nowhere')})

        assert refused.status_code == 422
        assert set(refused.json()) == set(succeeded.json())


class TestRouteIsDesktopOnly:
    def test_a_desktop_serves_storage(self, client: TestClient) -> None:
        assert client.get('/storage').status_code == 200


class TestVaultListing:
    """All remembered vaults, including closed entries (app.routers.storage._vaults)."""

    def test_an_untouched_config_lists_nothing(self, client: TestClient) -> None:
        assert client.get('/storage').json()['vaults'] == []

    def test_a_vault_is_listed_once_opened(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        chosen = tmp_path / 'first'
        chosen.mkdir()
        client.put('/storage', json={'path': str(chosen)})

        vaults = client.get('/storage').json()['vaults']
        assert [vault['name'] for vault in vaults] == ['first']
        assert vaults[0]['path'] == str(chosen.resolve())
        assert vaults[0]['open'] is True
        assert vaults[0]['available'] is True

    def test_the_most_recently_opened_comes_first(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        for name in ('older', 'newer'):
            folder = tmp_path / name
            folder.mkdir()
            client.put('/storage', json={'path': str(folder)})

        vaults = client.get('/storage').json()['vaults']
        assert [vault['name'] for vault in vaults] == ['newer', 'older']

    def test_a_vanished_vault_is_listed_as_unavailable(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        gone = tmp_path / 'gone'
        gone.mkdir()
        client.put('/storage', json={'path': str(gone)})
        still_here = tmp_path / 'still-here'
        still_here.mkdir()
        client.put('/storage', json={'path': str(still_here)})
        shutil.rmtree(gone)

        listed = {
            vault['name']: vault for vault in client.get('/storage').json()['vaults']
        }
        assert listed['gone']['available'] is False
        assert listed['still-here']['available'] is True

    def test_a_refused_folder_is_not_listed(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        client.put('/storage', json={'path': str(tmp_path / 'never-existed')})

        assert client.get('/storage').json()['vaults'] == []


class TestPreflight:
    def test_the_vault_header_survives_a_preflight(self, client: TestClient) -> None:
        answered = client.options(
            '/storage',
            headers={
                'Origin': 'tauri://localhost',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'X-Km-Vault',
            },
        )

        assert answered.status_code == 200, answered.text

    def test_every_header_a_client_sends_is_allowed(self, client: TestClient) -> None:
        from app.settings import ALLOWED_HEADERS

        answered = client.options(
            '/api/v1/artifacts',
            headers={
                'Origin': 'tauri://localhost',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': ', '.join(ALLOWED_HEADERS),
            },
        )

        assert answered.status_code == 200, answered.text

    def test_a_header_that_is_not_listed_is_not_allowed(
        self, client: TestClient
    ) -> None:
        answered = client.options(
            '/storage',
            headers={
                'Origin': 'tauri://localhost',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'X-Not-Allowed',
            },
        )

        allowed = answered.headers.get('access-control-allow-headers', '')
        assert 'x-not-allowed' not in allowed.lower()


class TestVaultHeader:
    """One engine, many vaults. `X-Km-Vault` selects request vault (app.dependencies.get_store)."""

    @staticmethod
    def two_vaults(client: TestClient, tmp_path: Path) -> dict[str, str]:
        """Open two vaults with second as default."""
        for name in ('vault-a', 'vault-b'):
            folder = tmp_path / name
            folder.mkdir()
            client.put('/storage', json={'path': str(folder)})
        return {
            vault['name']: vault['id']
            for vault in client.get('/storage').json()['vaults']
        }

    def test_no_header_serves_the_most_recently_opened(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        self.two_vaults(client, tmp_path)

        assert client.get('/ready').json()['storageRoot'] == str(
            (tmp_path / 'vault-b').resolve()
        )

    def test_a_header_serves_the_vault_it_names(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        ids = self.two_vaults(client, tmp_path)

        answered = client.get('/ready', headers={'X-Km-Vault': ids['vault-a']})

        assert answered.json()['storageRoot'] == str((tmp_path / 'vault-a').resolve())

    def test_an_unknown_vault_is_refused_rather_than_substituted(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        self.two_vaults(client, tmp_path)

        answered = client.get('/storage', headers={'X-Km-Vault': 'not-a-vault'})

        assert answered.status_code == 404

    def test_each_vault_keeps_its_own_artifacts(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        ids = self.two_vaults(client, tmp_path)
        into_a = {'X-Km-Vault': ids['vault-a']}
        into_b = {'X-Km-Vault': ids['vault-b']}

        created = client.post(
            '/api/v1/artifacts', json=creation_payload(), headers=into_a
        )
        assert created.status_code == 201, created.text

        assert len(client.get('/api/v1/artifacts', headers=into_a).json()) == 1
        assert client.get('/api/v1/artifacts', headers=into_b).json() == []
        assert list((tmp_path / 'vault-b').glob('*.md')) == []


class TestVaultCreation:
    @NOT_ROOT
    def test_a_refusal_names_the_first_fault_and_hides_the_rest(
        self, tmp_path: Path
    ) -> None:
        parent = tmp_path / 'parent'
        parent.mkdir()
        (parent / 'taken').mkdir()
        parent.chmod(0o500)
        try:
            through_storage = storage_router._why_a_vault_cannot_be_made(
                parent, 'taken'
            )
            through_vault = vault_service.why_a_vault_cannot_be_made(parent, 'taken')
        finally:
            parent.chmod(0o700)

        # Writability check precedes duplicate-name check in both services.
        assert 'is not writable' in through_storage
        assert 'already here' not in through_storage
        # Shared refusal order during storage-route migration (app.routers.vaults).
        assert through_vault == through_storage

    def test_a_vault_is_created_and_opened(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        response = client.post(
            '/storage/vaults', json={'parent': str(tmp_path), 'name': 'some-vault'}
        )

        assert response.status_code == 200, response.text
        assert (tmp_path / 'some-vault').is_dir()
        assert response.json()['storageName'] == 'some-vault'
        assert response.json()['storageReady'] is True
        assert app_config.configured_store_root() == (tmp_path / 'some-vault').resolve()

    def test_the_new_vault_is_what_ready_reports(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        client.post(
            '/storage/vaults', json={'parent': str(tmp_path), 'name': 'some-vault'}
        )

        assert client.get('/ready').json()['storageRoot'] == str(
            (tmp_path / 'some-vault').resolve()
        )

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('', 'A vault needs a name'),
            ('   ', 'A vault needs a name'),
            ('a/b', 'cannot contain a path separator'),
            ('..', 'cannot contain a path separator'),
        ],
    )
    def test_an_unusable_name_is_refused(
        self, client: TestClient, tmp_path: Path, name: str, expected: str
    ) -> None:
        response = client.post(
            '/storage/vaults', json={'parent': str(tmp_path), 'name': name}
        )

        assert response.status_code == 422
        assert expected in response.json()['storageDetail']

    def test_a_missing_parent_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        response = client.post(
            '/storage/vaults',
            json={'parent': str(tmp_path / 'not-there'), 'name': 'some-vault'},
        )

        assert response.status_code == 422
        assert 'does not exist' in response.json()['storageDetail']

    def test_a_parent_that_is_a_file_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        not_a_directory = tmp_path / 'notes.md'
        not_a_directory.write_text('hello', encoding='utf-8')

        response = client.post(
            '/storage/vaults',
            json={'parent': str(not_a_directory), 'name': 'some-vault'},
        )

        assert response.status_code == 422
        assert 'not a directory' in response.json()['storageDetail']

    @NOT_ROOT
    def test_an_unwritable_parent_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        locked = tmp_path / 'locked'
        locked.mkdir()
        locked.chmod(0o500)
        try:
            response = client.post(
                '/storage/vaults', json={'parent': str(locked), 'name': 'some-vault'}
            )
        finally:
            locked.chmod(0o700)

        assert response.status_code == 422
        assert 'not writable' in response.json()['storageDetail']

    def test_an_existing_name_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        (tmp_path / 'some-vault').mkdir()

        response = client.post(
            '/storage/vaults', json={'parent': str(tmp_path), 'name': 'some-vault'}
        )

        assert response.status_code == 422
        assert 'already here' in response.json()['storageDetail']

    def test_a_refusal_creates_nothing_and_changes_nothing(
        self, client: TestClient, store_root: Path, tmp_path: Path
    ) -> None:
        client.post(
            '/storage/vaults',
            json={'parent': str(tmp_path / 'not-there'), 'name': 'some-vault'},
        )

        assert not (tmp_path / 'not-there').exists()
        assert client.get('/ready').json()['storageRoot'] == str(store_root)

    def test_the_first_reason_wins_when_several_apply(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        answered = client.post(
            '/storage/vaults',
            json={'parent': str(tmp_path / 'missing'), 'name': ''},
        )

        assert answered.status_code == 422
        assert answered.json()['storageDetail'] == 'A vault needs a name'

    def test_a_folder_that_cannot_be_created_is_refused_not_crashed(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*_args: object, **_kwargs: object) -> None:
            raise OSError(28, 'No space left on device')

        monkeypatch.setattr('pathlib.Path.mkdir', refuse)
        answered = client.post(
            '/storage/vaults', json={'parent': str(tmp_path), 'name': 'roomy'}
        )

        assert answered.status_code == 422
        assert 'could not be created' in answered.json()['storageDetail']
        assert not (tmp_path / 'roomy').exists()


class TestVaultIdentity:
    @staticmethod
    def opened(client: TestClient, folder: Path) -> str:
        folder.mkdir(parents=True, exist_ok=True)
        client.put('/storage', json={'path': str(folder)})
        return next(
            vault['id']
            for vault in client.get('/storage').json()['vaults']
            if vault['path'] == str(folder.resolve())
        )

    def test_the_same_folder_twice_keeps_one_id(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        first = self.opened(client, tmp_path / 'once')
        second = self.opened(client, tmp_path / 'once')

        assert first == second
        assert len(client.get('/storage').json()['vaults']) == 1

    def test_an_id_survives_a_rename(self, client: TestClient, tmp_path: Path) -> None:
        identifier = self.opened(client, tmp_path / 'before')

        answered = client.patch(f'/storage/vaults/{identifier}', json={'name': 'after'})

        assert answered.status_code == 200, answered.text
        assert (tmp_path / 'after').is_dir()
        assert not (tmp_path / 'before').exists()
        listed = client.get('/storage').json()['vaults']
        assert [(v['id'], v['name']) for v in listed] == [(identifier, 'after')]

    def test_an_id_survives_a_move(self, client: TestClient, tmp_path: Path) -> None:
        identifier = self.opened(client, tmp_path / 'here' / 'vault')
        (tmp_path / 'elsewhere').mkdir()

        answered = client.patch(
            f'/storage/vaults/{identifier}',
            json={'parent': str(tmp_path / 'elsewhere')},
        )

        assert answered.status_code == 200, answered.text
        assert (tmp_path / 'elsewhere' / 'vault').is_dir()
        listed = client.get('/storage').json()['vaults']
        assert listed[0]['id'] == identifier
        assert listed[0]['path'] == str((tmp_path / 'elsewhere' / 'vault').resolve())

    def test_a_config_written_with_hash_ids_is_left_alone_not_re_keyed(
        self, client: TestClient, config_home: Path, tmp_path: Path
    ) -> None:
        folder = tmp_path / 'grandfathered'
        folder.mkdir()
        write_config_file(config_home, store_payload(folder))

        listed = client.get('/storage').json()['vaults']

        assert [vault['id'] for vault in listed] == ['abc123']
        assert (
            client.patch('/storage/vaults/abc123', json={'name': 'renamed'}).status_code
            == 200
        )
        assert [v['id'] for v in client.get('/storage').json()['vaults']] == ['abc123']

    def test_a_minted_id_is_sixteen_lowercase_hex_and_never_repeats(self) -> None:
        minted = app_config.new_store_id()

        assert re.fullmatch(r'[0-9a-f]{16}', minted)
        assert minted != app_config.new_store_id()

    def test_a_rename_does_not_make_a_vault_the_most_recently_opened(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        older = self.opened(client, tmp_path / 'older')
        self.opened(client, tmp_path / 'newer')

        client.patch(f'/storage/vaults/{older}', json={'name': 'older-renamed'})

        listed = client.get('/storage').json()['vaults']
        assert [vault['name'] for vault in listed] == ['newer', 'older-renamed']

    def test_artifacts_are_still_served_after_a_vault_moves(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        identifier = self.opened(client, tmp_path / 'here' / 'vault')
        made = create(client)
        (tmp_path / 'elsewhere').mkdir()

        client.patch(
            f'/storage/vaults/{identifier}',
            json={'parent': str(tmp_path / 'elsewhere')},
        )

        listed = client.get('/api/v1/artifacts').json()
        assert [item['id'] for item in listed] == [made['id']]


class TestVaultChange:
    def test_an_unknown_id_is_404_on_the_header_and_422_on_the_path(
        self, client: TestClient
    ) -> None:
        answered = client.patch('/storage/vaults/nope', json={'name': 'x'})

        assert answered.status_code == 422
        assert 'No vault with id nope' in answered.json()['storageDetail']

    def test_a_cross_filesystem_move_is_refused_and_moves_nothing(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / 'movable'
        identifier = TestVaultIdentity.opened(client, source)
        # Destination existence check precedes rename.
        elsewhere = tmp_path / 'elsewhere'
        elsewhere.mkdir()

        def cross_device(*_args: object, **_kwargs: object) -> None:
            raise OSError(errno.EXDEV, 'Cross-device link')

        monkeypatch.setattr('pathlib.Path.rename', cross_device)
        answered = client.patch(
            f'/storage/vaults/{identifier}', json={'parent': str(elsewhere)}
        )

        assert answered.status_code == 422
        assert 'could not be moved' in answered.json()['storageDetail']
        listed = next(
            vault
            for vault in client.get('/storage').json()['vaults']
            if vault['id'] == identifier
        )
        assert listed['path'] == str(source.resolve())
        assert source.is_dir()
        assert not (elsewhere / 'movable').exists()

    def test_changing_nothing_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'v')

        answered = client.patch(f'/storage/vaults/{identifier}', json={})

        assert answered.status_code == 422
        assert 'has to say what to change' in answered.json()['storageDetail']

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [('', 'needs a name'), ('a/b', 'path separator')],
    )
    def test_an_unusable_name_is_refused(
        self, client: TestClient, tmp_path: Path, name: str, expected: str
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'v')

        answered = client.patch(f'/storage/vaults/{identifier}', json={'name': name})

        assert answered.status_code == 422
        assert expected in answered.json()['storageDetail']

    def test_a_vanished_folder_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'gone')
        shutil.rmtree(tmp_path / 'gone')

        answered = client.patch(f'/storage/vaults/{identifier}', json={'name': 'x'})

        assert answered.status_code == 422
        assert 'not there any more' in answered.json()['storageDetail']

    def test_an_occupied_destination_is_refused(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'v')
        (tmp_path / 'taken').mkdir()

        answered = client.patch(f'/storage/vaults/{identifier}', json={'name': 'taken'})

        assert answered.status_code == 422
        assert 'already here' in answered.json()['storageDetail']

    def test_a_cross_device_move_is_refused_not_half_copied(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'v')
        (tmp_path / 'other-volume').mkdir()

        def refuse(*_args: object, **_kwargs: object) -> None:
            raise OSError(18, 'Cross-device link')

        monkeypatch.setattr('pathlib.Path.rename', refuse)
        answered = client.patch(
            f'/storage/vaults/{identifier}',
            json={'parent': str(tmp_path / 'other-volume')},
        )

        assert answered.status_code == 422
        assert 'could not be moved' in answered.json()['storageDetail']
        assert (tmp_path / 'v').is_dir()
        assert not (tmp_path / 'other-volume' / 'v').exists()


class TestVaultRemoval:
    def test_removing_drops_the_entry_and_leaves_the_folder(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        identifier = TestVaultIdentity.opened(client, tmp_path / 'keep-me')

        answered = client.delete(f'/storage/vaults/{identifier}')

        assert answered.status_code == 200, answered.text
        assert client.get('/storage').json()['vaults'] == []
        assert (tmp_path / 'keep-me').is_dir()

    def test_removing_the_default_repoints_it(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        TestVaultIdentity.opened(client, tmp_path / 'first')
        second = TestVaultIdentity.opened(client, tmp_path / 'second')

        client.delete(f'/storage/vaults/{second}')

        assert client.get('/ready').json()['storageRoot'] == str(
            (tmp_path / 'first').resolve()
        )

    def test_an_unknown_id_is_refused(self, client: TestClient) -> None:
        answered = client.delete('/storage/vaults/nope')

        assert answered.status_code == 422
