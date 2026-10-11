"""The folders a host describes, rebuilt in a private temporary folder."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from knowledge_mcp import bundled
from knowledge_mcp.contract import ScopeRequest
from knowledge_mcp.scope import ScopeError, Workspace

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def request(**overrides):
    base = {
        "folders": ["docs", "rfcs"],
        "universe_specs": [
            {
                "depth": 0,
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
    with Workspace(tmp_path).rebuilt(request(universe_specs=[])) as rebuilt:
        top = rebuilt.cwd.parent.parent
        names = sorted(path.name for path in (top / ".knowledge-bus").iterdir())
    assert names == sorted(rebuilt.bundled)
    assert "product-development.universe.kbp.yaml" in names
    assert "codebase-recordkeeping.type-guidance.kbp.yaml" in names
    assert all(name.endswith(".kbp.yaml") for name in names)


def test_an_empty_knowledge_bus_folder_below_definitions_stays_empty(tmp_path):
    with Workspace(tmp_path).rebuilt(
        request(
            universe_specs=[
                *request().model_dump()["universe_specs"],
                {"depth": 1, "files": []},
            ]
        )
    ) as rebuilt:
        empty = rebuilt.cwd.parent / ".knowledge-bus"
        assert empty.is_dir()
        assert list(empty.iterdir()) == []
        assert rebuilt.bundled == ["product-development.kbp.yaml"]


@pytest.mark.parametrize("depths", [[0], [1], [0, 2]])
def test_a_chain_without_definitions_means_the_bundled_set(tmp_path, depths):
    """A `.knowledge-bus/` holding only the record's plugin folder holds no definition."""
    specs = [{"depth": depth, "files": []} for depth in depths]
    with Workspace(tmp_path).rebuilt(request(universe_specs=specs)) as rebuilt:
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
            request(universe_specs=[{"depth": 0, "files": []}]), sent_only=True
        ),
    ):
        pass


def test_a_workspace_file_is_written_as_sent(tmp_path):
    with Workspace(tmp_path).rebuilt(
        request(
            universe_specs=[
                {"depth": 2, "files": [], "workspace_yaml": "from_parent: []\n"}
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
            "depth": 0,
            "files": [{"name": name, "id": "x", "version": "1", "text": "x: 1\n"}],
        }
    ]
    with (
        pytest.raises(ScopeError),
        Workspace(tmp_path).rebuilt(request(universe_specs=specs)),
    ):
        pass


def test_a_depth_beyond_the_document_folder_is_refused(tmp_path):
    with (
        pytest.raises(ScopeError),
        Workspace(tmp_path).rebuilt(
            request(universe_specs=[{"depth": 3, "files": []}])
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
            "depth": 0,
            "files": [
                {"name": "mine.kbp.yaml", "id": "mine", "version": "1", "text": text}
            ],
        }
    ]
    with workspace.rebuilt(request(universe_specs=sent)) as rebuilt:
        [received] = rebuilt.received
    by_digest = [
        {
            "depth": 0,
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
    with workspace.rebuilt(request(universe_specs=by_digest)) as again:
        top = again.cwd.parent.parent
        assert (top / ".knowledge-bus" / "mine.kbp.yaml").read_text() == text
        assert again.received == []
    with (
        pytest.raises(ScopeError, match=r"Send the text of mine\.kbp\.yaml"),
        Workspace(tmp_path / "other").rebuilt(request(universe_specs=by_digest)),
    ):
        pass


def test_an_unknown_universe_spec_without_text_asks_for_the_text(tmp_path):
    specs = [
        {"depth": 0, "files": [{"name": "mine.kbp.yaml", "id": "mine", "version": "1"}]}
    ]
    with (
        pytest.raises(ScopeError, match=r"Send the text of mine\.kbp\.yaml"),
        Workspace(tmp_path).rebuilt(request(universe_specs=specs)),
    ):
        pass


def test_host_text_overrides_matching_bundled_definition(tmp_path):
    text = (
        (FIXTURE_DIR / "product-development-universe-edited-label.yaml")
        .read_bytes()
        .decode("utf-8")
    )
    specs = [
        {
            "depth": 0,
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
    with Workspace(tmp_path).rebuilt(request(universe_specs=specs)) as rebuilt:
        assert (
            rebuilt.cwd.parent.parent / ".knowledge-bus" / "pd.kbp.yaml"
        ).read_text() == text
        assert rebuilt.bundled == []


def test_versions_sent_as_numbers_match_as_written():
    spec = request().universe_specs[0].files[0]
    assert spec.version == "0.9"
    numeric = ScopeRequest.model_validate(
        {
            "folders": [],
            "universe_specs": [
                {
                    "depth": 0,
                    "files": [{"name": "a.kbp.yaml", "id": "a", "version": 0.1}],
                }
            ],
        }
    )
    assert numeric.universe_specs[0].files[0].version == "0.1"


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
