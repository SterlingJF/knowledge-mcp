from __future__ import annotations

import hashlib
import re
from pathlib import Path

import anyio
import pytest
from mcp.client import Client

from knowledge_mcp import bundled
from knowledge_mcp.main import build_server
from knowledge_mcp.models import KnowledgeBusFolder, ScopeRequest
from knowledge_mcp.scope import SENT, ScopeError, Workspace
from knowledge_mcp.type_scope import Scopes

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def request(**overrides):
    base = {
        "folders": ["docs", "rfcs"],
        "knowledge_bus_folders": [
            {
                "folder": "",
                "files": [
                    {
                        "name": "product-development.kbp.yaml",
                        "id": "product-development",
                        "version": "0.9",
                    }
                ],
            }
        ],
    }
    return ScopeRequest.model_validate(base | overrides)


def test_rebuilt_scope_preserves_folder_chain_and_cleans_up(tmp_path):
    workspace = Workspace(tmp_path)
    with workspace.rebuilt(request()) as rebuilt:
        top = rebuilt.cwd.parent.parent
        assert rebuilt.cwd.relative_to(top).parts == ("docs", "rfcs")
        copy = top / ".knowledge-bus" / "product-development.kbp.yaml"
        assert (
            copy.read_bytes()
            == (
                bundled.UNIVERSES / "product-development" / "universe.kbp.yaml"
            ).read_bytes()
        )
        assert rebuilt.bundled == ["product-development.kbp.yaml"]
    assert not top.exists()


def test_identical_requests_reuse_rebuilt_directory_path(tmp_path):
    workspace = Workspace(tmp_path)
    with workspace.rebuilt(request()) as first:
        place = first.cwd
    with workspace.rebuilt(request()) as second:
        assert second.cwd == place


def test_no_knowledge_bus_folder_means_the_bundled_set(tmp_path):
    with Workspace(tmp_path).rebuilt(request(knowledge_bus_folders=[])) as rebuilt:
        top = rebuilt.cwd.parent.parent
        names = sorted(path.name for path in (top / ".knowledge-bus").iterdir())
    assert names == sorted(rebuilt.bundled)
    assert "product-development.universe.kbp.yaml" in names
    assert "codebase-recordkeeping.type-guidance.kbp.yaml" in names
    assert all(name.endswith(".kbp.yaml") for name in names)


def test_an_empty_knowledge_bus_folder_below_definitions_stays_empty(tmp_path):
    with Workspace(tmp_path).rebuilt(
        request(
            knowledge_bus_folders=[
                *request().model_dump()["knowledge_bus_folders"],
                {"folder": "docs", "files": []},
            ]
        )
    ) as rebuilt:
        empty = rebuilt.cwd.parent / ".knowledge-bus"
        assert empty.is_dir()
        assert list(empty.iterdir()) == []
        assert rebuilt.bundled == ["product-development.kbp.yaml"]


@pytest.mark.parametrize("depths", [[0], [1], [0, 2]])
def test_a_chain_without_definitions_means_the_bundled_set(tmp_path, depths):
    specs = [
        {"folder": "/".join(["docs", "rfcs"][:depth]), "files": []} for depth in depths
    ]
    with Workspace(tmp_path).rebuilt(request(knowledge_bus_folders=specs)) as rebuilt:
        top = rebuilt.cwd.parent.parent
        names = sorted(path.name for path in (top / ".knowledge-bus").iterdir())
        assert not (rebuilt.cwd / ".knowledge-bus").exists()
    assert names == sorted(rebuilt.bundled)
    assert "product-development.universe.kbp.yaml" in names
    assert rebuilt.nearest is None


def test_a_chain_without_definitions_is_refused_for_checking(tmp_path):
    with (
        pytest.raises(ScopeError, match="send the text of each"),
        Workspace(tmp_path).rebuilt(
            request(knowledge_bus_folders=[{"folder": "", "files": []}]), sent_only=True
        ),
    ):
        pass


def test_a_workspace_file_is_written_as_sent(tmp_path):
    with Workspace(tmp_path).rebuilt(
        request(
            knowledge_bus_folders=[
                {
                    "folder": "docs/rfcs",
                    "files": [],
                    "workspace_yaml": "from_parent: []\n",
                }
            ]
        )
    ) as rebuilt:
        assert (
            rebuilt.cwd / ".knowledge-bus" / "workspace.yaml"
        ).read_text() == "from_parent: []\n"


@pytest.mark.parametrize("folder", ["..", ".", "a/b", "a\\b", "", "nul\0"])
def test_unsafe_folder_names_are_refused(tmp_path, folder):
    with (
        pytest.raises(ScopeError),
        Workspace(tmp_path).rebuilt(request(folders=[folder])),
    ):
        pass


@pytest.mark.parametrize(
    "name", ["../x.kbp.yaml", "x.yaml", "workspace.yaml", ".kbp.yaml", "a/b.kbp.yaml"]
)
def test_invalid_definition_filenames_are_rejected(tmp_path, name):
    specs = [
        {
            "folder": "",
            "files": [{"name": name, "id": "x", "version": "1", "text": "x: 1\n"}],
        }
    ]
    with (
        pytest.raises(ScopeError),
        Workspace(tmp_path).rebuilt(request(knowledge_bus_folders=specs)),
    ):
        pass


def test_a_depth_beyond_the_document_folder_is_refused(tmp_path):
    with (
        pytest.raises(ScopeError),
        Workspace(tmp_path).rebuilt(
            request(knowledge_bus_folders=[{"folder": "docs/rfcs/notes", "files": []}])
        ),
    ):
        pass


def test_definition_digest_reuses_text_only_in_same_workspace(tmp_path):
    workspace = Workspace(tmp_path)
    text = (
        (FIXTURE_DIR / "universe-with-id-and-version-only.yaml")
        .read_bytes()
        .decode("utf-8")
    )
    sent = [
        {
            "folder": "",
            "files": [
                {"name": "mine.kbp.yaml", "id": "mine", "version": "1", "text": text}
            ],
        }
    ]
    with workspace.rebuilt(request(knowledge_bus_folders=sent)) as rebuilt:
        [received] = rebuilt.received
    by_digest = [
        {
            "folder": "",
            "files": [
                {
                    "name": "mine.kbp.yaml",
                    "id": "mine",
                    "version": "1",
                    "digest": received["digest"],
                }
            ],
        }
    ]
    with workspace.rebuilt(request(knowledge_bus_folders=by_digest)) as again:
        top = again.cwd.parent.parent
        assert (top / ".knowledge-bus" / "mine.kbp.yaml").read_text() == text
        assert again.received == []
    with (
        pytest.raises(ScopeError, match=r"Send the text of mine\.kbp\.yaml"),
        Workspace(tmp_path / "other").rebuilt(request(knowledge_bus_folders=by_digest)),
    ):
        pass


def test_an_unknown_universe_spec_without_text_asks_for_the_text(tmp_path):
    specs = [
        {
            "folder": "",
            "files": [{"name": "mine.kbp.yaml", "id": "mine", "version": "1"}],
        }
    ]
    with (
        pytest.raises(ScopeError, match=r"Send the text of mine\.kbp\.yaml"),
        Workspace(tmp_path).rebuilt(request(knowledge_bus_folders=specs)),
    ):
        pass


def test_harness_text_overrides_matching_bundled_definition(tmp_path):
    text = (
        (FIXTURE_DIR / "product-development-universe-edited-label.yaml")
        .read_bytes()
        .decode("utf-8")
    )
    specs = [
        {
            "folder": "",
            "files": [
                {
                    "name": "pd.kbp.yaml",
                    "id": "product-development",
                    "version": "0.9",
                    "text": text,
                }
            ],
        }
    ]
    with Workspace(tmp_path).rebuilt(request(knowledge_bus_folders=specs)) as rebuilt:
        assert (
            rebuilt.cwd.parent.parent / ".knowledge-bus" / "pd.kbp.yaml"
        ).read_text() == text
        assert rebuilt.bundled == []


def test_versions_sent_as_numbers_match_as_written():
    spec = request().knowledge_bus_folders[0].files[0]
    assert spec.version == "0.9"
    numeric = ScopeRequest.model_validate(
        {
            "folders": [],
            "knowledge_bus_folders": [
                {
                    "folder": "",
                    "files": [{"name": "a.kbp.yaml", "id": "a", "version": 0.1}],
                }
            ],
        }
    )
    assert numeric.knowledge_bus_folders[0].files[0].version == "0.1"


def test_bundled_ref_is_the_knowledge_bus_pin():
    pyproject = (bundled.PLUGIN / "pyproject.toml").read_text()
    pin = re.search(
        r"knowledge-bus @ https://github\.com/SterlingJF/knowledge-bus/releases/download/([^/\"]+)/",
        pyproject,
    )
    assert pin is not None
    assert bundled.ref() == pin.group(1)
    assert ("product-development", "0.9") in bundled.index()
    assert ("codebase-recordkeeping-guidance", "0.1") in bundled.index()


def digest_request(data: bytes, **overrides):
    spec = request().knowledge_bus_folders[0].files[0]
    spec.digest = "sha256:" + hashlib.sha256(data).hexdigest()
    return request(
        knowledge_bus_folders=[{"folder": "", "files": [spec.model_dump() | overrides]}]
    )


def test_cold_four_bundle_digests_preserve_bytes_and_provenance(tmp_path):
    copies = bundled.copies()
    assert len(copies) == 4
    specs = [
        {
            "name": copy.name,
            "id": copy.id,
            "version": copy.version,
            "digest": "sha256:" + hashlib.sha256(copy.path.read_bytes()).hexdigest(),
        }
        for copy in copies
    ]
    scope = request(knowledge_bus_folders=[{"folder": "", "files": specs}])
    workspace = Workspace(tmp_path)
    with workspace.rebuilt(scope) as rebuilt:
        top = rebuilt.cwd.parent.parent / ".knowledge-bus"
        assert [(top / copy.name).read_bytes() for copy in copies] == [
            copy.path.read_bytes() for copy in copies
        ]
        assert rebuilt.received == []
        assert rebuilt.bundled == [copy.name for copy in copies]
        assert rebuilt.sources == {copy.id: bundled.label() for copy in copies}
    assert all(workspace.recall(spec["digest"]) is None for spec in specs)


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "custom"},
        {"version": "99"},
        {"id": "codebase-recordkeeping", "version": "0.1"},
        {"digest": "malformed"},
        {"digest": "sha256:" + "0" * 64},
    ],
)
def test_cold_bundle_digest_misses_request_exact_text(tmp_path, overrides):
    copy = bundled.index()["product-development", "0.9"]
    with (
        pytest.raises(ScopeError, match="Send the text") as error,
        Workspace(tmp_path).rebuilt(
            digest_request(copy.path.read_bytes(), **overrides)
        ),
    ):
        pass
    assert error.value.code == "digest-unknown"
    assert error.value.errors == [
        (
            "No text for product-development.kbp.yaml.",
            "#/knowledge_bus_folders/0/files/0/digest",
        )
    ]


def test_edited_custom_digest_requires_full_text_then_reuses_it(tmp_path):
    copy = bundled.index()["product-development", "0.9"]
    data = copy.path.read_bytes() + b"\n# local edit\n"
    scope = digest_request(data)
    workspace = Workspace(tmp_path)
    with pytest.raises(ScopeError), workspace.rebuilt(scope):
        pass
    sent = digest_request(data, text=data.decode("utf-8"))
    with workspace.rebuilt(sent) as rebuilt:
        assert rebuilt.received == [
            {
                "name": "product-development.kbp.yaml",
                "digest": scope.knowledge_bus_folders[0].files[0].digest,
            }
        ]
    with workspace.rebuilt(scope, sent_only=True) as rebuilt:
        assert rebuilt.bundled == []
        assert rebuilt.sources == {copy.id: SENT}
        assert (
            rebuilt.cwd.parent.parent / ".knowledge-bus/product-development.kbp.yaml"
        ).read_bytes() == data


def test_bundle_resolution_never_establishes_sent_context(tmp_path):
    copy = bundled.index()["product-development", "0.9"]
    data = copy.path.read_bytes()
    scope = digest_request(data)
    workspace = Workspace(tmp_path)
    for primed in (False, True):
        if primed:
            with workspace.rebuilt(scope):
                pass
        with (
            pytest.raises(ScopeError, match="never validates a bundled copy"),
            workspace.rebuilt(scope, sent_only=True),
        ):
            pass
    with workspace.rebuilt(
        digest_request(data, text=data.decode("utf-8")), sent_only=True
    ):
        pass
    with workspace.rebuilt(scope, sent_only=True) as rebuilt:
        assert rebuilt.sources == {copy.id: SENT}
        assert rebuilt.bundled == []


@pytest.mark.parametrize(
    "data",
    [
        b"universe:\r\n  id: product-development\r\n  version: '0.9'\r\n",
        b"\xef\xbb\xbfuniverse:\n  id: product-development\n  version: '0.9'\n",
    ],
)
def test_bundle_digest_preserves_raw_utf8(tmp_path, monkeypatch, data):
    directory = tmp_path / "universes" / "test"
    directory.mkdir(parents=True)
    (directory / "universe.kbp.yaml").write_bytes(data)
    monkeypatch.setattr(bundled, "UNIVERSES", directory.parent)
    bundled.copies.cache_clear()
    try:
        workspace = Workspace(tmp_path / "work")
        with workspace.rebuilt(digest_request(data)) as rebuilt:
            assert (
                rebuilt.cwd.parent.parent
                / ".knowledge-bus/product-development.kbp.yaml"
            ).read_bytes() == data
            assert rebuilt.sources == {"product-development": bundled.label()}
            assert rebuilt.received == []
        normalized = (
            data.decode("utf-8")
            .replace("\r\n", "\n")
            .removeprefix("\ufeff")
            .encode("utf-8")
        )
        with pytest.raises(ScopeError), workspace.rebuilt(digest_request(normalized)):
            pass
        assert (
            workspace.recall(
                digest_request(data).knowledge_bus_folders[0].files[0].digest
            )
            is None
        )
    finally:
        bundled.copies.cache_clear()


@pytest.mark.parametrize("change", ["bytes", "id", "version", "utf8", "missing"])
def test_bundle_digest_rechecks_package_bytes_and_header(tmp_path, monkeypatch, change):
    path = tmp_path / "package.kbp.yaml"
    data = b"universe:\n  id: product-development\n  version: '0.9'\n"
    path.write_bytes(data)
    copy = bundled.Copy(path.name, "product-development", "0.9", path)
    monkeypatch.setattr(bundled, "index", lambda: {(copy.id, copy.version): copy})
    workspace = Workspace(tmp_path / "work")
    with workspace.rebuilt(digest_request(data)):
        pass
    changed = {
        "bytes": data + b"# changed\n",
        "id": data.replace(b"product-development", b"other"),
        "version": data.replace(b"0.9", b"99"),
        "utf8": data + b"\xff",
        "missing": data,
    }[change]
    path.write_bytes(changed)
    if change == "missing":
        path.unlink()
    supplied = data if change in ("bytes", "missing") else changed
    with pytest.raises(ScopeError), workspace.rebuilt(digest_request(supplied)):
        pass


def test_cold_four_digest_sdk_response_matches_header_bundle_source(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))

    async def ask(digests):
        specs = []
        for copy in bundled.copies():
            spec = {"name": copy.name, "id": copy.id, "version": copy.version}
            if digests:
                spec["digest"] = (
                    "sha256:" + hashlib.sha256(copy.path.read_bytes()).hexdigest()
                )
            specs.append(spec)
        async with Client(
            build_server(Workspace(tmp_path / str(digests))), mode="legacy"
        ) as client:
            return await client.call_tool(
                "kb_get_document_type",
                {
                    "location": "private-repo/docs/design.md",
                    "name": "design.md",
                    "folders": ["docs"],
                    "knowledge_bus_folders": [{"folder": "", "files": specs}],
                },
            )

    header = anyio.run(ask, False)
    digest = anyio.run(ask, True)
    assert not header.is_error
    assert not digest.is_error
    assert digest == header
    assert digest.structured_content["received"] == []
    assert all(
        spec["source"] == bundled.label()
        for spec in digest.structured_content["universe_specs"]
    )


@pytest.mark.parametrize(
    "data",
    [
        b"\xff",
        b"universe:\n  id: product-development\n  version: '0.9'\n# corrupt: \xff\n",
    ],
)
def test_cold_index_corrupt_utf8_requests_text(tmp_path, monkeypatch, data):
    directory = tmp_path / "universes" / "test"
    directory.mkdir(parents=True)
    (directory / "universe.kbp.yaml").write_bytes(data)
    monkeypatch.setattr(bundled, "UNIVERSES", directory.parent)
    bundled.copies.cache_clear()
    try:
        with (
            pytest.raises(ScopeError, match="Send the text") as error,
            Workspace(tmp_path / "work").rebuilt(digest_request(data)),
        ):
            pass
        assert error.value.code == "digest-unknown"
        assert error.value.errors == [
            (
                "No text for product-development.kbp.yaml.",
                "#/knowledge_bus_folders/0/files/0/digest",
            )
        ]
    finally:
        bundled.copies.cache_clear()


@pytest.mark.parametrize("root", ["digest", "header", "implicit"])
def test_mixed_crlf_definition_compares_exact_content(tmp_path, monkeypatch, root):
    copy = bundled.index()["product-development", "0.9"]
    data = copy.path.read_bytes().replace(b"\n", b"\r\n")
    directory = tmp_path / "universes" / "test"
    directory.mkdir(parents=True)
    (directory / "universe.kbp.yaml").write_bytes(data)
    monkeypatch.setattr(bundled, "UNIVERSES", directory.parent)
    bundled.copies.cache_clear()
    try:
        for number, nested in enumerate(
            (data, data.replace(b"\r\n", b"\n"), data + b"# edit\r\n")
        ):
            spec = digest_request(data).knowledge_bus_folders[0].files[0]
            if root == "header":
                spec.digest = None
            folders = (
                []
                if root == "implicit"
                else [KnowledgeBusFolder(folder="", files=[spec])]
            )
            folders.append(
                KnowledgeBusFolder(
                    folder="nested",
                    files=[
                        spec.model_copy(
                            update={"text": nested.decode("utf-8"), "digest": None}
                        )
                    ],
                )
            )
            workspace = Workspace(tmp_path / f"work-{number}")
            scopes = Scopes(workspace, folders)
            assert scopes.same_definition("a.md", "nested/b.md", copy.id) == (
                nested == data
            )
            assert scopes.same_definition("a.md", "nested/b.md", copy.id) == (
                nested == data
            )
    finally:
        bundled.copies.cache_clear()
