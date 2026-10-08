# File: server/tests/test_codec.py

from __future__ import annotations

from typing import Any

from app.store import codec

BASE: dict[str, Any] = {
    "id": "11111111-1111-4111-8111-111111111111",
    "projectId": None,
    "universe": {"id": "product-development", "version": "0.5"},
    "artifactType": "ayx0k",
    "name": "Storage backend for the local-first MVP",
    "status": "DRAFT",
    "version": 1,
    "createdBy": "local-principal:tester",
    "createdAt": "2026-08-19T09:00:00Z",
    "updatedAt": "2026-08-19T09:00:00Z",
    "lastReviewedDate": None,
    "provenance": {"contextArtifactIds": []},
    "links": {},
}


def _record(**overrides: Any) -> dict[str, Any]:
    record = {
        "id": "aaaaaaaa-1111-4111-8111-111111111111",
        "element": "e43c2",
        "value": "Files, not a database.",
        "asserted_by": "local-principal:tester",
        "binding_on": [],
        "status": "contracted",
        "observed_at": "2026-08-19T09:00:00Z",
        "supersedes": None,
        "exhaustive": "unknown",
    }
    record.update(overrides)
    return record


def test_round_trip_preserves_top_level_data_and_links():
    artifact = {
        **BASE,
        "data": {"e43c2": [_record()]},
        "links": {
            "eyhkm": [
                {
                    "artifactId": "22222222-1111-4111-8111-111111111111",
                    "instanceId": "33333333-1111-4111-8111-111111111111",
                }
            ]
        },
    }
    raw = codec.to_bytes(artifact, {"e43c2": "Decision"})
    parsed, prose_keys, coercions = codec.from_bytes(raw)

    assert coercions == []
    assert prose_keys == {"e43c2": "Decision"}
    for key in (
        "id",
        "universe",
        "artifactType",
        "name",
        "status",
        "version",
        "data",
        "links",
    ):
        assert parsed[key] == artifact[key]


def test_no_op_write_is_byte_identical():
    artifact = {**BASE, "data": {"e43c2": [_record()]}}
    first = codec.to_bytes(artifact, {"e43c2": "Decision"})
    parsed, prose_keys, _ = codec.from_bytes(first)
    second = codec.to_bytes(parsed, prose_keys)

    assert first == second
    assert codec.compute_etag(first) == codec.compute_etag(second)


def test_top_level_key_order_is_not_alphabetical():
    raw = codec.to_bytes({**BASE, "data": {}}, {}).decode()
    assert raw.index("\nid:") < raw.index("\nartifactType:") < raw.index("\ncreatedAt:")


def test_prose_lifts_to_the_body_when_one_live_instance():
    artifact = {**BASE, "data": {"e43c2": [_record(value="A decision, in prose.")]}}
    raw = codec.to_bytes(artifact, {"e43c2": "Decision"}).decode()

    assert "## Decision" in raw
    assert "A decision, in prose." in raw.split("---", 2)[2]


def test_prose_stays_inline_when_two_live_instances():
    artifact = {
        **BASE,
        "data": {
            "e43c2": [
                _record(id="a1", value="One"),
                _record(
                    id="a2", value="Two", asserted_by="agent:knowledge-mcp-structure"
                ),
            ]
        },
    }
    raw = codec.to_bytes(artifact, {"e43c2": "Decision"}).decode()

    assert "## Decision" not in raw
    parsed, _, _ = codec.from_bytes(raw.encode())
    assert [record["value"] for record in parsed["data"]["e43c2"]] == ["One", "Two"]


def test_prose_stays_inline_when_whitespace_is_significant():
    artifact = {**BASE, "data": {"e43c2": [_record(value="  padded  ")]}}
    raw = codec.to_bytes(artifact, {"e43c2": "Decision"})

    assert b"## Decision" not in raw
    parsed, _, _ = codec.from_bytes(raw)
    assert parsed["data"]["e43c2"][0]["value"] == "  padded  "


def test_multi_paragraph_prose_survives_the_body():
    value = "First paragraph.\n\nSecond paragraph."
    artifact = {**BASE, "data": {"e43c2": [_record(value=value)]}}
    parsed, _, _ = codec.from_bytes(codec.to_bytes(artifact, {"e43c2": "Decision"}))

    assert parsed["data"]["e43c2"][0]["value"] == value


def test_hand_typed_yaml_is_coerced_and_reported():
    raw = b"""---
id: 11111111-1111-4111-8111-111111111111
version: 1
name: Hand typed by a person
status: DRAFT
createdBy: local-principal:tester
createdAt: 2026-05-18T10:00:00Z
lastReviewedDate: 2025-05-18
universe:
  id: product-development
  version: 0.5
data:
  e43c2:
  - id: aaaaaaaa-1111-4111-8111-111111111111
    element: e43c2
    value: a decision
    asserted_by: local-principal:tester
    status: contracted
    observed_at: 2026-05-18
    supersedes: null
    exhaustive: unknown
    binding_on: []
links: {}
---
"""
    parsed, _, coercions = codec.from_bytes(raw)
    paths = {coercion["path"] for coercion in coercions}

    assert paths == {
        "createdAt",
        "lastReviewedDate",
        "universe.version",
        "data.e43c2[0].observed_at",
    }
    assert parsed["universe"]["version"] == "0.5"
    assert parsed["lastReviewedDate"] == "2025-05-18T00:00:00Z"
    assert parsed["data"]["e43c2"][0]["observed_at"] == "2026-05-18T00:00:00Z"


def test_filenames_are_sanitised_and_identity_is_the_id():
    name = "Detailed Analysis: Manual Invoicing Process"
    filename = codec.sanitise_filename(name, "abcd1234-1111-4111-8111-111111111111")

    assert ":" not in filename
    assert filename.endswith(".md")
    assert codec.sanitise_filename("///", "abcd1234") == "abcd1234.md"


def test_etag_moves_with_content_and_is_not_stored():
    artifact = {**BASE, "data": {"e43c2": [_record()]}}
    raw = codec.to_bytes(artifact, {})
    changed = codec.to_bytes({**artifact, "name": "A different name entirely"}, {})

    assert codec.compute_etag(raw) != codec.compute_etag(changed)
    assert b"sha256-" not in raw
    assert codec.compute_etag(raw).startswith('"sha256-')
