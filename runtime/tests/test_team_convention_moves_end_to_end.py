from __future__ import annotations

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.test_document_move_end_to_end import apply, arguments, invoke, prepare, vault
from tests.test_team_conventions_end_to_end import spec


def test_m01_m04_cross_team_links():
    docs = vault()
    plan = prepare(docs, path="Finance/Note.md")
    after = apply(docs, plan)
    assert "Finance/Note.md" in records.parse(plan["record"])
    expected = {
        "Inbox/Note.md",
        "References/assets/diagram.png",
        "Other/Reference.md",
        "Inbox/Space Name.md",
        "Same/Index.md",
        "References/Index.md",
    }
    assert {e["target_before"] for e in plan["links"] if e["target_before"]} <= expected
    for link in plan["links"]:
        assert link["target_after"] == (
            "Finance/Note.md"
            if link["target_before"] == "Inbox/Note.md"
            else link["target_before"]
        )
    assert "[plain](../Finance/Note.md)" in after["References/Index.md"]


def test_m02_destination_type_absent():
    docs = vault()
    a = prepare(
        docs,
        path="Engineering/Note.md",
        knowledge_bus_folders=[spec("Engineering", "engineering")],
    )
    assert a["status"] == "blocked"
    assert a["writes"] == []
    assert any(i["code"] == "destination-type-conflict" for i in a["issues"])


def test_m03_reused_definition_blocks():
    docs = vault()
    a = prepare(
        docs,
        path="Finance/Note.md",
        knowledge_bus_folders=[
            spec(
                "Finance",
                "product-development",
                [("Product development", "Different meaning")],
            )
        ],
    )
    assert a["status"] == "blocked"
    assert not a["writes"]


def test_m05_ambiguous_cross_team_links_block():
    docs = vault()
    docs["Other/Reference.md"] = "[[Index]]"
    a = prepare(docs, path="Finance/Note.md")
    assert a["status"] == "blocked"
    assert not a["writes"]
    assert any(i["code"] == "link-ambiguous" for i in a["issues"])


def test_m06_cross_team_search_echo():
    docs = vault()
    args = arguments(docs, path="Finance/Note.md")
    server = build_server()
    first = invoke(server, args)
    assert first["status"] == "texts_needed"
    args.update(searched=True, search=[*first["search"], "altered"])
    second = invoke(server, args)
    assert second["status"] == "texts_needed"
    assert second["writes"] == []


def test_m08_cross_team_recovery():
    docs = vault()
    original = dict(docs)
    plan = prepare(docs, path="Finance/Note.md")
    first = plan["writes"][0]
    after = apply(docs, {**plan, "writes": [first]})
    assert records.digest(after[first["path"]]) == first["after_digest"]
    after.pop(first["path"])
    after[first["old_path"]] = original[first["old_path"]]
    assert after == original
