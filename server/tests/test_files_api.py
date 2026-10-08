from __future__ import annotations

from typing import TYPE_CHECKING

from tests.conftest import create

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi.testclient import TestClient


def test_files_list_every_content_file_and_artifacts_remain_structured(
    client: TestClient, store_root: Path
):
    artifact = create(client)
    (store_root / "Atlas" / "plain.md").write_text("plain note", encoding="utf-8")
    (store_root / "x" / "source.pdf").write_bytes(b"%PDF-1.7")
    (store_root / "outside.txt").write_text("outside", encoding="utf-8")
    (store_root / ".knowledge-mcp" / "config.json").write_text("{}", encoding="utf-8")
    hidden = store_root / "Efforts" / ".hidden"
    hidden.mkdir()
    (hidden / "secret.txt").write_text("secret", encoding="utf-8")

    files = client.get("/api/v1/files").json()
    artifact_path = next((store_root / "Efforts").glob("artifact-*.md"))

    assert [item["path"] for item in files] == [
        "Atlas/plain.md",
        artifact_path.relative_to(store_root).as_posix(),
        "x/source.pdf",
    ]
    assert all(item["absolutePath"].startswith(str(store_root)) for item in files)
    assert [item["id"] for item in client.get("/api/v1/artifacts").json()] == [
        artifact["id"]
    ]


def test_markdown_is_inline_and_other_files_are_retrieved_by_path(
    client: TestClient, store_root: Path
):
    note = store_root / "Calendar" / "today.md"
    note.write_text("# Today\n", encoding="utf-8")
    attachment = store_root / "x" / "diagram.png"
    attachment.write_bytes(b"\x89PNG\r\n")

    markdown = client.get("/api/v1/files/Calendar/today.md")
    binary = client.get("/api/v1/files/x/diagram.png")

    assert markdown.status_code == 200
    assert markdown.json()["content"] == "# Today\n"
    assert markdown.json()["absolutePath"] == str(note)
    assert binary.status_code == 200
    assert binary.json()["content"] is None
    assert binary.json()["absolutePath"] == str(attachment)


def test_files_follow_visible_symlinks_and_stop_cycles(
    client: TestClient, store_root: Path, tmp_path: Path
):
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")
    file_alias = store_root / "x" / "outside.txt"
    file_alias.symlink_to(outside_file)

    outside_directory = tmp_path / "outside-directory"
    outside_directory.mkdir()
    (outside_directory / "linked.md").write_text("linked", encoding="utf-8")
    (outside_directory / "loop").symlink_to(outside_directory, target_is_directory=True)
    directory_alias = store_root / "Atlas" / "reference"
    directory_alias.symlink_to(outside_directory, target_is_directory=True)

    broken_alias = store_root / "x" / "missing.pdf"
    broken_alias.symlink_to(tmp_path / "missing.pdf")

    files = client.get("/api/v1/files").json()

    assert [item["path"] for item in files] == [
        "Atlas/reference/linked.md",
        "x/missing.pdf",
        "x/outside.txt",
    ]
    linked = client.get("/api/v1/files/Atlas/reference/linked.md").json()
    assert linked["content"] == "linked"
    assert linked["absolutePath"] == str(directory_alias / "linked.md")
    assert client.get("/api/v1/files/x/outside.txt").json()["absolutePath"] == str(
        file_alias
    )
    assert client.get("/api/v1/files/x/missing.pdf").json()["content"] is None
    assert client.get("/api/v1/files/%2E%2E/outside.txt").status_code == 404


def test_files_have_no_depth_limit(client: TestClient, store_root: Path):
    directory = store_root / "Efforts"
    for index in range(12):
        directory /= str(index)
    directory.mkdir(parents=True)
    note = directory / "deep.md"
    note.write_text("still visible", encoding="utf-8")

    relative = note.relative_to(store_root).as_posix()

    assert relative in [item["path"] for item in client.get("/api/v1/files").json()]
    assert client.get(f"/api/v1/files/{relative}").json()["content"] == "still visible"
