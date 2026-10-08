# File: server/tests/test_vault.py

from __future__ import annotations

import ast
import errno
import json
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from app.api_models_auto import VaultFolderName
from app.factory import create_app
from app.settings import load_settings
from app.store import file_store
from app.store.vaults import VaultStores
from app.vault import layout
from app.vault import service as vault_service

NOT_ROOT = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="Permission bits do not restrain root",
)


def folders_in(root: Path) -> set[str]:
    return {entry.name for entry in root.iterdir() if entry.is_dir()}


def importers_of(module: str, *, within: str) -> list[str]:
    package = Path(__file__).resolve().parents[1] / "app" / within
    offenders = []
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                module
            ):
                offenders.append(path.name)
                break
            if isinstance(node, ast.Import) and any(
                alias.name.startswith(module) for alias in node.names
            ):
                offenders.append(path.name)
                break
    return offenders


def write_config(config_home: Path, path: Path) -> None:
    """Write `abc123` vault entry directly to config."""
    config_home.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "stores": {
            "abc123": {
                "type": "filesystem",
                "path": str(path),
                "lastOpened": 1,
                "open": True,
            }
        },
    }
    (config_home / "config.json").write_text(json.dumps(payload), encoding="utf-8")


class TestTheModuleBoundary:
    """Vault and store depend separately on the contract. Composition root supplies `on_new_root`."""

    def test_the_store_does_not_import_the_vault(self) -> None:
        offenders = importers_of("app.vault", within="store")

        assert offenders == [], (
            f"{offenders} import app.vault. The store needs the declared folders, not the vault "
            "module: read VaultFolderName from app.api_models_auto, or take it as an argument."
        )

    def test_the_vault_does_not_import_the_store(self) -> None:
        assert importers_of("app.store", within="vault") == []

    def test_both_read_the_same_declaration(self) -> None:
        assert tuple(folder.value for folder in VaultFolderName) == layout.VAULT_FOLDERS

    def test_the_store_and_the_vault_agree_on_content(self) -> None:
        # Vault excludes CONFIG_FOLDER. Store excludes dot prefixes.
        assert file_store.CONTENT_FOLDERS == layout.CONTENT_FOLDERS

    def test_every_content_folder_survives_the_scan_prune(self) -> None:
        for name in file_store.CONTENT_FOLDERS:
            assert not name.startswith(".")
            assert name not in file_store.SKIPPED_DIRECTORIES

    def test_the_config_folder_is_pruned_by_the_scan(self) -> None:
        assert (
            layout.CONFIG_FOLDER.startswith(".")
            or layout.CONFIG_FOLDER in file_store.SKIPPED_DIRECTORIES
        )


class TestTheDeclaredShape:
    def test_the_folders_come_from_the_contract(self) -> None:
        assert layout.VAULT_FOLDERS == (
            "+",
            "x",
            "Atlas",
            "Calendar",
            "Efforts",
            ".knowledge-mcp",
        )

    def test_config_is_scaffolded_and_is_not_content(self) -> None:
        assert layout.CONFIG_FOLDER in layout.VAULT_FOLDERS
        assert layout.CONFIG_FOLDER not in layout.CONTENT_FOLDERS

    def test_ensure_reports_what_it_found_rather_than_what_it_made(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "Atlas").mkdir()

        state = {folder.name: folder.adopted for folder in layout.ensure(tmp_path)}

        assert state["Atlas"] is True
        assert state["Efforts"] is False

    @NOT_ROOT
    def test_an_opening_refusal_names_the_first_fault(self, tmp_path: Path) -> None:
        not_a_folder = tmp_path / "a-file"
        not_a_folder.write_text("x", encoding="utf8")
        not_a_folder.chmod(0o000)
        try:
            refusal = vault_service.why_a_folder_cannot_be_opened(not_a_folder)
        finally:
            not_a_folder.chmod(0o600)

        assert "is not a folder" in refusal
        assert "readable and writable" not in refusal

    def test_a_second_pass_changes_nothing(self, tmp_path: Path) -> None:
        layout.ensure(tmp_path)
        before = sorted(folders_in(tmp_path))

        again = layout.ensure(tmp_path)

        assert sorted(folders_in(tmp_path)) == before
        assert all(folder.adopted for folder in again)


class TestOpeningAFolder:
    def test_a_new_vault_is_created_with_its_folders(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        answered = client.post(
            "/storage/vaults", json={"parent": str(tmp_path), "name": "made-here"}
        )

        assert answered.status_code == 200
        assert folders_in(tmp_path / "made-here") == set(layout.VAULT_FOLDERS)

    def test_an_existing_folder_keeps_what_it_has_and_gains_the_rest(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        adopted = tmp_path / "already-here"
        (adopted / "Atlas").mkdir(parents=True)
        (adopted / "Notes").mkdir()
        (adopted / "Notes" / "kept.md").write_text("mine", encoding="utf8")

        client.put("/storage", json={"path": str(adopted)})

        assert set(layout.VAULT_FOLDERS) <= folders_in(adopted)
        assert (adopted / "Notes" / "kept.md").read_text(encoding="utf8") == "mine"

    def test_opening_twice_changes_nothing(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        twice = tmp_path / "twice"
        twice.mkdir()
        client.put("/storage", json={"path": str(twice)})
        before = sorted(folders_in(twice))

        client.put("/storage", json={"path": str(twice)})

        assert sorted(folders_in(twice)) == before

    def test_a_refused_folder_is_not_scaffolded(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        not_a_folder = tmp_path / "a-file"
        not_a_folder.write_text("", encoding="utf8")

        answered = client.put("/storage", json={"path": str(not_a_folder)})

        assert answered.status_code == 422
        assert not_a_folder.is_file()


class TestEveryRouteIntoARoot:
    def test_a_vault_opened_from_config_at_boot_has_its_folders(
        self, tmp_path: Path
    ) -> None:
        # Client fixture uses returning-user launch path (tests.conftest.client).
        root = tmp_path / "from-config"
        root.mkdir()
        settings = load_settings(STORE_ROOT=root, KM_ROLE="desktop")

        with TestClient(create_app(settings)) as client:
            client.get("/api/v1/artifacts")

        assert folders_in(root) == set(layout.VAULT_FOLDERS)

    def test_a_vault_reached_only_by_its_header_has_its_folders(
        self, client: TestClient, config_home: Path, tmp_path: Path
    ) -> None:
        remembered = tmp_path / "by-header"
        remembered.mkdir()
        write_config(config_home, remembered)

        client.get("/api/v1/artifacts", headers={"X-Km-Vault": "abc123"})

        assert folders_in(remembered) == set(layout.VAULT_FOLDERS)

    def test_a_moved_vault_carries_its_folders(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        source = tmp_path / "before-move"
        source.mkdir()
        identifier = client.put("/storage", json={"path": str(source)}).json()[
            "vaults"
        ][0]["id"]

        client.patch(f"/storage/vaults/{identifier}", json={"name": "after-move"})

        assert folders_in(tmp_path / "after-move") == set(layout.VAULT_FOLDERS)


class TestWhereTheGuaranteeStops:
    def test_folders_deleted_under_a_live_store_are_not_restored(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        live = tmp_path / "live"
        live.mkdir()
        client.put("/storage", json={"path": str(live)})
        shutil.rmtree(live)
        live.mkdir()

        client.get("/api/v1/artifacts")

        assert folders_in(live) == set()

    def test_a_root_that_cannot_be_prepared_is_logged_not_raised(
        self, tmp_path: Path
    ) -> None:
        def refuse(_root: Path) -> None:
            raise OSError(30, "Read-only file system")

        vaults = VaultStores(tmp_path, on_new_root=refuse)

        with capture_logs() as logged:
            store = vaults.for_root(tmp_path)

        assert store.root == tmp_path
        assert [entry["log_level"] for entry in logged] == ["warning"]
        assert logged[0]["reason"] == "Read-only file system"


class TestTheContractedRoutes:
    """Contract-typed `/api/v1/vaults` routes. Old shape remains in `routers.storage`."""

    def test_creating_a_vault_reports_six_folders_it_made(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        answered = client.post(
            "/api/v1/vaults", json={"parent": str(tmp_path), "name": "fresh"}
        )

        assert answered.status_code == 201
        made = {
            folder["name"]: folder["adopted"] for folder in answered.json()["folders"]
        }
        assert set(made) == set(layout.VAULT_FOLDERS)
        assert not any(made.values())

    def test_opening_reports_which_folders_were_already_there(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        existing = tmp_path / "existing"
        (existing / "Atlas").mkdir(parents=True)
        (existing / "Notes").mkdir()

        answered = client.post("/api/v1/vaults/open", json={"path": str(existing)})

        assert answered.status_code == 200
        found = {
            folder["name"]: folder["adopted"] for folder in answered.json()["folders"]
        }
        assert found["Atlas"] is True
        assert found["Efforts"] is False
        assert (existing / "Notes").is_dir()

    def test_a_json_body_without_a_content_type_is_read_as_json(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        folder = tmp_path / "untyped"
        folder.mkdir()
        selection = {"path": str(folder)}
        # The first open makes the six folders, so both answers below adopt all six.
        client.post("/api/v1/vaults/open", json=selection)

        typed = client.post("/api/v1/vaults/open", json=selection)
        untyped = client.post("/api/v1/vaults/open", content=json.dumps(selection))

        assert "content-type" not in untyped.request.headers
        assert untyped.status_code == typed.status_code == 200
        assert {**untyped.json(), "lastOpened": None} == {
            **typed.json(),
            "lastOpened": None,
        }

    def test_the_list_puts_the_most_recently_opened_first(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        client.post("/api/v1/vaults", json={"parent": str(tmp_path), "name": "older"})
        client.post("/api/v1/vaults", json={"parent": str(tmp_path), "name": "newer"})

        listed = [vault["name"] for vault in client.get("/api/v1/vaults").json()]

        assert listed[:2] == ["newer", "older"]

    def test_a_created_vault_becomes_the_header_less_default(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        made = client.post(
            "/api/v1/vaults", json={"parent": str(tmp_path), "name": "now-default"}
        ).json()

        assert client.get("/storage").json()["storageRoot"] == made["path"]

    def test_an_opened_vault_becomes_the_header_less_default(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        adopted = tmp_path / "adopted"
        adopted.mkdir()

        opened = client.post("/api/v1/vaults/open", json={"path": str(adopted)}).json()

        assert client.get("/storage").json()["storageRoot"] == opened["path"]

    def test_a_duplicate_name_is_refused_with_a_reason(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        client.post("/api/v1/vaults", json={"parent": str(tmp_path), "name": "twice"})

        answered = client.post(
            "/api/v1/vaults", json={"parent": str(tmp_path), "name": "twice"}
        )

        assert answered.status_code == 422
        assert answered.json()["reason"] == "Something called twice is already here"

    def test_an_unknown_vault_is_a_404_on_every_verb(self, client: TestClient) -> None:
        assert client.get("/api/v1/vaults/nope").status_code == 404
        assert (
            client.patch("/api/v1/vaults/nope", json={"name": "x"}).status_code == 404
        )
        assert client.delete("/api/v1/vaults/nope").status_code == 404

    def test_a_vault_is_renamed_listed_and_forgotten(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        made = client.post(
            "/api/v1/vaults", json={"parent": str(tmp_path), "name": "before"}
        ).json()

        renamed = client.patch(f"/api/v1/vaults/{made['id']}", json={"name": "after"})
        assert renamed.status_code == 200
        assert renamed.json()["name"] == "after"
        assert renamed.json()["id"] == made["id"]

        assert client.delete(f"/api/v1/vaults/{made['id']}").status_code == 204
        listed = [vault["id"] for vault in client.get("/api/v1/vaults").json()]
        assert made["id"] not in listed
        assert (tmp_path / "after").is_dir()

    def test_a_create_that_cannot_make_the_folder_is_refused_not_crashed(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refuse(*_args: object, **_kwargs: object) -> None:
            raise OSError(28, "No space left on device")

        monkeypatch.setattr("pathlib.Path.mkdir", refuse)
        answered = client.post(
            "/api/v1/vaults", json={"parent": str(tmp_path), "name": "roomy"}
        )

        assert answered.status_code == 422
        assert "could not be created" in answered.json()["reason"]
        assert not (tmp_path / "roomy").exists()

    def test_a_cross_filesystem_move_is_refused_and_moves_nothing(
        self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source_parent = tmp_path / "here"
        source_parent.mkdir()
        # Destination existence check precedes rename.
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        made = client.post(
            "/api/v1/vaults", json={"parent": str(source_parent), "name": "movable"}
        ).json()

        def cross_device(*_args: object, **_kwargs: object) -> None:
            raise OSError(errno.EXDEV, "Cross-device link")

        monkeypatch.setattr("pathlib.Path.rename", cross_device)
        answered = client.patch(
            f"/api/v1/vaults/{made['id']}", json={"parent": str(elsewhere)}
        )

        assert answered.status_code == 422
        assert "could not be moved" in answered.json()["reason"]
        # monkeypatch.undo() reverts XDG_CONFIG_HOME. Config writes use os.replace (atomic_write).
        assert client.get(f"/api/v1/vaults/{made['id']}").json()["path"] == made["path"]
        assert (source_parent / "movable").is_dir()
        assert not (elsewhere / "movable").exists()


class TestWhatIsNotTouched:
    def test_listing_vaults_does_not_scaffold_them(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        remembered = tmp_path / "remembered"
        remembered.mkdir()
        client.put("/storage", json={"path": str(remembered)})
        shutil.rmtree(remembered)
        remembered.mkdir()

        client.get("/storage")

        assert folders_in(remembered) == set()
