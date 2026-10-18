from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from knowledge_mcp import document_types as record
from tests.document_types_harness import LINE, Harness, KnowledgeBase
from tests.harness import (
    CODEBASE,
    PRODUCT,
    server_parameters,
    session,
    texts,
    validator,
)

KINDS: record.Kinds = {
    CODEBASE: ("0.1", frozenset({"readme", "design-proposal"})),
    PRODUCT: ("0.9", frozenset({"design-doc", "decision-record"})),
}
ALLOWED = record.AllowedBy(basis="instruction", text=LINE, location="AGENTS.md")


@dataclass
class Fit:
    path: str
    set_by: record.SetBy = "agent"
    universe_spec: str | None = None
    document_type: str | None = None
    no_document_type: bool = False
    audience: record.Audience | None = None


def entry(**fields: Any) -> record.Entry:
    base = {
        "set_by": "agent",
        "allowed_by": ALLOWED,
        "time": "2026-10-10T09:00:00.000Z",
    }
    return record.entry(**(base | fields))


def merge(files: record.Files, **options: Any) -> record.Merged:
    defaults = {
        "events": [],
        "entries": [],
        "recheck": False,
        "kinds_at": lambda _path: KINDS,
        "allowed_by": ALLOWED,
        "fingerprints": {},
    }
    return record.merge(files, record.MergeRequest(**defaults | options))


def test_the_written_record_reads_back_and_meets_its_contract():
    files = {
        "docs/rfcs/0042-cache.md": entry(
            universe_spec=CODEBASE, version="0.1", document_type="design-proposal"
        ),
        "vendor-quote.md": entry(
            no_document_type=True, fingerprint="sha256:" + "a" * 64
        ),
        "docs/product/pricing.md": entry(
            universe_spec=PRODUCT,
            version="0.9",
            document_type="design-doc",
            set_by="person",
            audience=record.Audience(value="the product lead", status="confirmed"),
        ),
    }

    text = record.dump(files)

    assert text.startswith("# Your agent rewrites this file")
    assert record.parse(text) == files
    data = yaml.safe_load(text)
    validator("document-types").validate(data)
    assert list(data["files"]) == sorted(files)
    assert isinstance(data["files"]["vendor-quote.md"]["time"], str)
    assert data["files"]["docs/rfcs/0042-cache.md"]["version"] == "0.1"


def test_parse_coerces_unquoted_version_and_timestamp_to_strings():
    text = (
        "schema: knowledge-mcp/document-types/1\n"
        "files:\n"
        "  README.md:\n"
        "    universe_spec: codebase-recordkeeping\n"
        "    version: 0.1\n"
        "    document_type: readme\n"
        "    set_by: person\n"
        "    allowed_by: {basis: request, text: It is the readme.}\n"
        "    time: 2026-10-10T09:00:00Z\n"
    )

    [(path, read)] = record.parse(text).items()

    assert path == "README.md"
    assert (read.version, read.time) == ("0.1", "2026-10-10T09:00:00Z")


def test_an_empty_text_is_an_empty_record():
    assert record.parse("") == {}
    assert record.parse("# nothing yet\n") == {}


@pytest.mark.parametrize(
    "text",
    [
        "files: {}\n",
        "schema: knowledge-mcp/fit-record/2\nfiles: {}\n",
        "schema: knowledge-mcp/document-types/1\nfiles: {}\nextra: 1\n",
        "schema: knowledge-mcp/document-types/1\nfiles:\n  a.md: {set_by: agent, time: x}\n",
        "schema: [unclosed\n",
        "schema: knowledge-mcp/document-types/1\nfiles:\n  ../a.md:\n    no_document_type: true\n",
    ],
)
def test_parse_rejects_malformed_or_invalid_records(text):
    with pytest.raises(record.DocumentTypesError):
        record.parse(text)


@pytest.mark.parametrize(
    "path", ["/etc/passwd", "../outside.md", "docs//a.md", "a\\b.md", "", "docs/./a.md"]
)
def test_normal_path_rejects_absolute_and_malformed_paths(path):
    with pytest.raises(record.DocumentTypesError):
        record.normal_path(path)


def test_normal_path_removes_leading_dot_slash():
    assert record.normal_path("./docs/a.md") == "docs/a.md"


class TestCompare:
    def test_a_rename_is_caught_by_its_fingerprint(self):
        files = {"docs/a.md": entry(no_document_type=True, fingerprint="f1")}

        events = record.compare(files, {"docs/b.md": "f1", "docs/c.md": "f2"})

        assert events == [
            ("moved", "docs/b.md", "docs/a.md", "f1"),
            ("created", "docs/c.md", None, "f2"),
        ]

    def test_unique_filename_detects_move_without_fingerprints(self):
        files = {
            "docs/a.md": entry(no_document_type=True),
            "docs/gone.md": entry(no_document_type=True),
        }

        events = record.compare(files, {"archive/a.md": None})

        assert events == [
            ("moved", "archive/a.md", "docs/a.md", None),
            ("deleted", "docs/gone.md", None, None),
        ]

    def test_duplicate_filenames_prevent_move_detection(self):
        files = {
            "a/notes.md": entry(no_document_type=True),
            "b/notes.md": entry(no_document_type=True),
        }

        events = record.compare(files, {"c/notes.md": None})

        assert sorted(events) == [
            ("created", "c/notes.md", None, None),
            ("deleted", "a/notes.md", None, None),
            ("deleted", "b/notes.md", None, None),
        ]

    def test_changed_fingerprint_emits_fingerprint_event(self):
        files = {"a.md": entry(no_document_type=True, fingerprint="old")}

        assert record.compare(files, {"a.md": "new"}) == [
            ("fingerprint", "a.md", None, "new")
        ]
        assert record.compare(files, {"a.md": None}) == []

    def test_conflicting_fingerprints_prevent_filename_move_detection(self):
        files = {
            "old/notes.md": entry(
                no_document_type=True, set_by="person", fingerprint="f1"
            )
        }

        events = record.compare(files, {"new/notes.md": "f2"})

        assert events == [
            ("deleted", "old/notes.md", None, None),
            ("created", "new/notes.md", None, "f2"),
        ]

    def test_one_missing_fingerprint_allows_unique_filename_move(self):
        files = {"old/notes.md": entry(no_document_type=True, fingerprint="f1")}

        assert record.compare(files, {"new/notes.md": None}) == [
            ("moved", "new/notes.md", "old/notes.md", None)
        ]

    def test_listing_events_convert_to_change_request_fields(self):
        assert [
            record.as_change(event)
            for event in [
                ("moved", "b.md", "a.md", "f1"),
                ("deleted", "c.md", None, None),
                ("created", "d.md", None, None),
                ("fingerprint", "e.md", None, "f2"),
            ]
        ] == [
            {
                "change": "moved",
                "path": "b.md",
                "old_path": "a.md",
                "fingerprint": "f1",
            },
            {"change": "deleted", "path": "c.md"},
            {"change": "created", "path": "d.md"},
            {"change": "edited", "path": "e.md", "fingerprint": "f2"},
        ]


class TestMerge:
    def test_a_correction_wins_over_a_later_fit(self):
        files = {
            "a.md": entry(
                universe_spec=PRODUCT,
                version="0.9",
                document_type="design-doc",
                set_by="person",
            )
        }

        merged = merge(
            files,
            entries=[
                Fit("a.md", universe_spec=CODEBASE, document_type="design-proposal")
            ],
        )

        assert merged.files == files
        assert [change["change"] for change in merged.changed] == ["kept"]

    def test_a_correction_replaces_a_fit(self):
        files = {
            "a.md": entry(
                universe_spec=CODEBASE, version="0.1", document_type="design-proposal"
            )
        }

        merged = merge(
            files,
            entries=[
                Fit(
                    "a.md",
                    set_by="person",
                    universe_spec=PRODUCT,
                    document_type="design-doc",
                )
            ],
        )

        assert merged.files["a.md"].set_by == "person"
        assert merged.files["a.md"].version == "0.9"
        [change] = merged.changed
        assert change["change"] == "corrected"
        assert change["was"]["document_type"] == "design-proposal"

    def test_audience_correction_preserves_document_type(self):
        files = {
            "a.md": entry(
                universe_spec=PRODUCT, version="0.9", document_type="design-doc"
            )
        }
        reader = record.Audience(value="engineering", status="confirmed")

        merged = merge(files, entries=[Fit("a.md", set_by="person", audience=reader)])

        assert merged.files["a.md"].audience == reader
        assert merged.files["a.md"].document_type == "design-doc"
        assert merged.files["a.md"].set_by == "person"

    def test_a_refit_to_the_same_type_keeps_the_reader(self):
        reader = record.Audience(value="the product lead", status="confirmed")
        files = {
            "a.md": entry(
                universe_spec=PRODUCT,
                version="0.9",
                document_type="design-doc",
                audience=reader,
            )
        }

        merged = merge(
            files,
            entries=[Fit("a.md", universe_spec=PRODUCT, document_type="design-doc")],
        )

        assert merged.files == files
        assert merged.changed == []

    def test_a_document_type_out_of_scope_is_refused(self):
        with pytest.raises(record.DocumentTypesError, match="kbp_kinds"):
            merge(
                {}, entries=[Fit("a.md", universe_spec=PRODUCT, document_type="readme")]
            )

    def test_a_fit_naming_both_a_type_and_no_fit_is_refused(self):
        with pytest.raises(record.DocumentTypesError, match="no_document_type"):
            merge(
                {},
                entries=[
                    Fit(
                        "a.md",
                        universe_spec=PRODUCT,
                        document_type="design-doc",
                        no_document_type=True,
                    )
                ],
            )

    def test_move_out_of_universe_scope_queues_correction_for_refit(self):
        files = {
            "team/a.md": entry(
                universe_spec=PRODUCT,
                version="0.9",
                document_type="design-doc",
                set_by="person",
            )
        }

        def kinds_at(path: str) -> record.Kinds:
            return KINDS if path.startswith("team/") else {CODEBASE: KINDS[CODEBASE]}

        merged = merge(
            files,
            events=[("moved", "code/a.md", "team/a.md", None)],
            kinds_at=kinds_at,
        )

        assert merged.files == {}
        assert merged.settle["code/a.md"].was == files["team/a.md"]

    def test_deleted_correction_includes_note_to_consult_user(self):
        files = {
            "a.md": entry(no_document_type=True, set_by="person"),
            "b.md": entry(no_document_type=True),
        }

        merged = merge(
            files,
            events=[("deleted", "a.md", None, None), ("deleted", "b.md", None, None)],
        )

        assert merged.files == {}
        noted, plain = merged.changed
        assert "ask the person" in noted["note"]
        assert "note" not in plain

    def test_refit_queues_only_uncorrected_files(self):
        files = {
            "a.md": entry(no_document_type=True),
            "b.md": entry(no_document_type=True, set_by="person"),
        }

        assert list(merge(files, recheck=True).settle) == ["a.md"]

    def test_pending_fingerprint_is_saved_when_file_is_fitted_later(self):
        fingerprints: dict[str, str] = {}
        merge({}, events=[("created", "a.md", None, "f1")], fingerprints=fingerprints)

        later = merge(
            {}, entries=[Fit("a.md", no_document_type=True)], fingerprints=fingerprints
        )

        assert later.files["a.md"].fingerprint == "f1"


def ask(state: Path, *calls: tuple[str, dict]) -> list:
    async def steps(client):
        return [await client.call_tool(name, arguments) for name, arguments in calls]

    return session(server_parameters(state), steps)


def test_missing_basis_returns_no_record_or_digest(tmp_path):
    base = KnowledgeBase(None)
    base.write("README.md", "# Readme\n")
    harness = Harness(base)
    fits = [{"path": "README.md", "set_by": "agent", "no_document_type": True}]

    [result] = ask(
        tmp_path,
        (
            "kb_prepare_document_types",
            {"location": base.location, "record": "", "entries": fits},
        ),
    )

    assert not result.is_error, texts(result)
    answer = json.loads(texts(result)[0])
    validator("document-types-update").validate(answer)
    assert answer["record"] is None and answer["digest"] is None
    assert "`allowed_by`" in answer["note"]
    assert [change["change"] for change in answer["changed"]] == ["settled"]
    assert harness.record() == ""


def test_nested_definitions_select_separate_file_scopes(tmp_path):
    base = KnowledgeBase(None)
    base.add_universe_specs("", [CODEBASE])
    base.add_universe_specs("team", [PRODUCT])
    harness = Harness(base)
    listing = [{"path": "README.md"}, {"path": "team/docs/pricing.md"}]

    [result] = ask(
        tmp_path,
        (
            "kb_prepare_document_types",
            {
                "location": base.location,
                "record": "",
                "knowledge_bus_folders": harness.universe_specs(),
                "listing": listing,
            },
        ),
    )

    answer = json.loads(texts(result)[0])
    scopes = {item["path"]: item["scope"] for item in answer["to_settle"]}
    ids = [
        [spec["id"] for spec in scope["universe_specs"]] for scope in answer["scopes"]
    ]
    assert ids[scopes["README.md"]] == [CODEBASE]
    assert ids[scopes["team/docs/pricing.md"]] == [PRODUCT]


def test_files_inside_a_knowledge_bus_folder_stay_out_of_the_record(tmp_path):
    configuration = [
        ".knowledge-bus/plugins/knowledge-mcp/record.yaml",
        "team/.knowledge-bus/x.kbp.yaml",
    ]
    listing = [{"path": "README.md"}, *({"path": path} for path in configuration)]

    [listed] = ask(
        tmp_path,
        (
            "kb_prepare_document_types",
            {
                "location": "/kb",
                "record": "",
                "listing": listing,
                "allowed_by": {"basis": "instruction", "text": LINE},
            },
        ),
    )
    answer = json.loads(texts(listed)[0])
    [settled] = ask(
        tmp_path,
        (
            "kb_prepare_document_types",
            {
                "location": "/kb",
                "record": "",
                "entries": [
                    {"path": "README.md", "set_by": "agent", "no_document_type": True}
                ],
                "changes": answer["listing_changes"],
                "allowed_by": {"basis": "instruction", "text": LINE},
            },
        ),
    )

    validator("document-types-update").validate(answer)
    assert [item["path"] for item in answer["to_settle"]] == ["README.md"]
    assert [change["path"] for change in answer["listing_changes"]] == ["README.md"]
    assert answer["record"] is None
    merged = json.loads(texts(settled)[0])["record"]
    assert list(yaml.safe_load(merged)["files"]) == ["README.md"]
    for path in configuration:
        assert path not in merged


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "Send `record`"),
        ({"record": "", "record_digest": "sha256:" + "0" * 64}, "never both"),
        ({"record_digest": "sha256:" + "0" * 64}, "holds no text"),
        ({"record": "schema: other\n"}, "schema"),
        ({"record": "", "listing": [{"path": "/etc/passwd"}]}, "root folder"),
        ({"record": "", "allowed_by": {"basis": "instruction"}}, "allowed_by/text"),
        (
            {"record": "", "changes": [{"change": "edited", "path": "a.md"}]},
            "fingerprint",
        ),
        (
            {
                "record": "",
                "entries": [
                    {
                        "path": "a.md",
                        "set_by": "agent",
                        "universe_spec": PRODUCT,
                        "document_type": "not-a-type",
                    }
                ],
            },
            "not-a-type",
        ),
    ],
)
def test_invalid_fit_record_requests_are_rejected_and_logged(
    tmp_path, arguments, message
):
    [result] = ask(
        tmp_path, ("kb_prepare_document_types", {"location": "/kb", **arguments})
    )

    assert result.is_error
    assert message in texts(result)[0]
    log = (tmp_path / "knowledge-mcp" / "log.jsonl").read_text().splitlines()
    assert json.loads(log[-1])["returned"] == texts(result)
