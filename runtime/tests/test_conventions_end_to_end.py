from __future__ import annotations

import json

import anyio
import pytest
import yaml

from knowledge_mcp.main import build_server
from tests.harness import PRODUCT, server_parameters, session, texts

PLACE = ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"
PERMISSION = {"basis": "accepted_change", "text": "Save the convention."}


def upsert(**extra):
    return dict(
        change="upsert",
        universe_spec=PRODUCT,
        document_type="decision-record",
        folder=["Decisions"],
        name={"separator": " ", "parts": [{"part": "content"}]},
        content={"label": "document title", "instruction": "Read the first heading."},
        set_by="person",
        **extra,
    )


def stored(*changes):
    entries = []
    for change in changes or [upsert()]:
        entries.append(
            {k: v for k, v in change.items() if k != "change"}
            | {"allowed_by": PERMISSION, "time": "2026-10-18T00:00:00Z"}
        )
    return yaml.safe_dump(
        {
            "schema": "knowledge-mcp/conventions/1",
            "from_parent": [],
            "conventions": entries,
        },
        sort_keys=False,
    )


def invoke(server=None, **args):
    result = anyio.run(
        (server or build_server()).call_tool,
        "kb_prepare_conventions",
        {"location": "unreachable://vault", "conventions": "", **args},
    )
    answer = result.structured_content
    if not result.is_error:
        assert json.loads(texts(result)[0]) == answer
    return answer


def test_a01_a16_read_absent_and_no_file_access():
    a = invoke()
    assert a["status"] == "unchanged"
    assert a["current"] == []
    assert a["record"] is a["digest"] is None


def test_a02_a03_first_save_and_permission():
    assert invoke(changes=[upsert()])["status"] == "permission_needed"
    a = invoke(changes=[upsert()], allowed_by=PERMISSION)
    assert a["status"] == "ready"
    entry = yaml.safe_load(a["record"])["conventions"][0]
    assert entry["allowed_by"] == PERMISSION
    assert entry["time"].endswith("Z")
    assert entry["name"]["case"] == "as-written"


def test_a04_a07_replacement_removal_and_noops():
    text = stored()
    a = invoke(conventions=text, changes=[upsert()], allowed_by=PERMISSION)
    assert a["status"] == "unchanged"
    change = upsert()
    change["folder"] = ["Archive"]
    a = invoke(conventions=text, changes=[change], allowed_by=PERMISSION)
    assert yaml.safe_load(a["record"])["conventions"][0]["folder"] == ["Archive"]
    remove = {
        k: v for k, v in upsert().items() if k in ("universe_spec", "document_type")
    }
    remove["change"] = "remove"
    a = invoke(conventions=text, changes=[remove], allowed_by=PERMISSION)
    assert a["allowed_by"] == PERMISSION
    assert yaml.safe_load(a["record"])["conventions"] == []
    assert invoke(changes=[remove])["status"] == "unchanged"
    result = anyio.run(
        build_server().call_tool,
        "kb_record_edit",
        {
            "location": "unreachable://vault/" + PLACE,
            "allowed_by": PERMISSION,
            "before": text,
            "after": a["record"],
            "whole_file": True,
        },
    )
    assert not result.is_error
    assert result.structured_content["allowed_by"] == PERMISSION


@pytest.mark.parametrize(
    "text",
    [
        "[",
        "schema: wrong",
        stored().replace("from_parent: []", "extra: true\nfrom_parent: []"),
    ],
)
def test_a08_invalid_configuration(text):
    a = invoke(conventions=text)
    assert a["type"].endswith("/conventions-invalid")
    assert a["errors"][0]["pointer"].startswith("#/conventions")


def test_a09_duplicate_pairs():
    assert invoke(conventions=stored(upsert(), upsert()))["type"].endswith(
        "/conventions-invalid"
    )
    assert invoke(changes=[upsert(), upsert()])["type"].endswith("/conventions-invalid")


def test_a10_a11_unknown_and_retained_stale_type():
    stale = upsert()
    stale["document_type"] = "vanished"
    assert invoke(changes=[stale], allowed_by=PERMISSION)["type"].endswith(
        "/document-type-unknown"
    )
    a = invoke(conventions=stored(stale), changes=[upsert()], allowed_by=PERMISSION)
    assert {e["document_type"] for e in yaml.safe_load(a["record"])["conventions"]} == {
        "vanished",
        "decision-record",
    }


def test_a12_a13_digests():
    server = build_server()
    a = invoke(server, conventions=stored())
    result = anyio.run(
        server.call_tool,
        "kb_prepare_conventions",
        {"location": "vault", "conventions_digest": a["based_on"]},
    )
    assert result.structured_content["current"] == a["current"]
    assert invoke(conventions_digest=a["based_on"])["type"].endswith(
        "/argument-invalid"
    )
    result = anyio.run(
        build_server().call_tool,
        "kb_prepare_conventions",
        {"location": "vault", "conventions_digest": "sha256:" + "0" * 64},
    )
    assert result.structured_content["type"].endswith("/digest-unknown")


def test_a14_concurrent_retry_preserves_unrelated_change():
    other = upsert()
    other["document_type"] = "design-doc"
    first = invoke(changes=[upsert()], allowed_by=PERMISSION)
    concurrent = invoke(changes=[other], allowed_by=PERMISSION)
    assert first["based_on"] != concurrent["digest"]
    retry = invoke(
        conventions=concurrent["record"], changes=[upsert()], allowed_by=PERMISSION
    )
    assert len(yaml.safe_load(retry["record"])["conventions"]) == 2


def test_a15_parent_selection():
    data = yaml.safe_load(stored())
    data["from_parent"] = [
        {"universe_spec": PRODUCT, "document_type": "decision-record"}
    ]
    assert invoke(conventions=yaml.safe_dump(data))["type"].endswith(
        "/conventions-unsupported"
    )


def test_stdio_preparation(tmp_path):
    async def steps(client):
        result = await client.call_tool(
            "kb_prepare_conventions",
            {
                "location": "unreachable://vault",
                "conventions": "",
                "changes": [upsert()],
                "allowed_by": PERMISSION,
            },
        )
        assert not result.is_error, texts(result)
        assert result.structured_content["status"] == "ready"

    session(server_parameters(tmp_path / "state"), steps)
