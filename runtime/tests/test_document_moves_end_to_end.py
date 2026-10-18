from __future__ import annotations

import json
from pathlib import Path

import anyio
import pytest

from knowledge_mcp import document_move
from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.test_filing_end_to_end import PERMISSION, typed
from tests.test_team_conventions_end_to_end import spec


def arguments(docs, moves, **extra):
    return dict(
        location="unreachable://vault",
        moves=[dict(old_path=a, path=b) for a, b in moves],
        listing=[dict(path=p) for p in docs],
        documents=[dict(path=p, text=t) for p, t in docs.items()],
        case_mode="sensitive",
        knowledge_bus_folders=[],
        record=records.dump({p: typed() for p in docs}),
        **extra,
    )


def invoke(server, args):
    result = anyio.run(server.call_tool, "kb_prepare_document_moves", args)
    assert not result.is_error, result.structured_content
    assert json.loads(result.content[0].text) == result.structured_content
    return result.structured_content


def prepare(docs, moves, permission=True, **extra):
    server = build_server()
    args = arguments(docs, moves, **extra)
    if permission:
        args["allowed_by"] = PERMISSION
    first = invoke(server, args)
    if first["status"] != "texts_needed":
        return first
    return invoke(server, {**args, "searched": True, "search": first["search"]})


def apply(docs, plan):
    assert plan["status"] == "ready", plan["issues"]
    for w in plan["writes"]:
        assert records.digest(docs[w["old_path"]]) == w["before_digest"]
    after = {
        p: t
        for p, t in docs.items()
        if p not in {w["old_path"] for w in plan["writes"]}
    }
    after.update({w["path"]: w["text"] for w in plan["writes"]})
    return after


@pytest.mark.parametrize(
    "moves",
    [
        [("A.md", "Decisions/Alpha.md"), ("B.md", "Decisions/Beta.md")],
        [("A.md", "B.md"), ("B.md", "A.md")],
        [("A.md", "B.md"), ("B.md", "C.md")],
        [("A.md", "B.md"), ("B.md", "C.md"), ("C.md", "A.md")],
    ],
)
def test_simultaneous_identities_and_classifications(moves):
    docs = {
        a: f"identity:{a}\n[[A#Heading|alpha]] [beta](B.md#^block)" for a, _ in moves
    }
    expected = dict(moves)
    plan = prepare(docs, moves)
    after = apply(docs, plan)
    for old, new in moves:
        assert after[new].startswith(f"identity:{old}\n")
        assert "#Heading|alpha]]" in after[new] and "#^block)" in after[new]
    for link in plan["links"]:
        assert link["target_after"] == expected[link["target_before"]]
    assert set(records.parse(plan["record"])) == set(expected.values())
    assert len(plan["writes"]) == len(moves)


def test_shared_and_moving_referrers_encoded_and_outside_folder():
    docs = {
        "Inbox/A.md": "[b](B.md#Heading)",
        "Inbox/B.md": "[[A]]",
        "Outside/Index.md": "[[A]] [b](../Inbox/%42.md)",
    }
    a = prepare(docs, [("Inbox/A.md", "D/Alpha.md"), ("Inbox/B.md", "E/Beta.md")])
    after = apply(docs, a)
    assert after["D/Alpha.md"] == "[b](../E/Beta.md#Heading)"
    assert after["E/Beta.md"] == "[[Alpha]]"
    assert after["Outside/Index.md"] == "[[Alpha]] [b](../E/Beta.md)"
    assert len(a["writes"]) == 3
    preview = prepare(
        docs,
        [("Inbox/A.md", "D/Alpha.md"), ("Inbox/B.md", "E/Beta.md")],
        permission=False,
    )
    assert (
        preview["status"] == "permission_needed"
        and preview["writes"] == []
        and preview["record"] is None
    )
    assert {r["old_path"] for r in preview["affected_documents"]} == set(docs)


def test_changed_and_dropped_rows_and_explicit_blocked_drop():
    docs = {"A.md": "[[B]]", "B.md": "[[A]]", "Stay.md": "[[A]] [[B]]"}
    blocked = prepare(docs, [("A.md", "B.md")])
    assert blocked["status"] == "blocked" and not blocked["writes"]
    changed = prepare(docs, [("A.md", "Chosen.md")])
    after = apply(docs, changed)
    assert after["B.md"] == "[[Chosen]]" and "Stay.md" in after
    assert prepare(docs, [])["status"] == "unchanged"


@pytest.mark.parametrize(
    "moves", [[("A.md", "C.md"), ("B.md", "C.md")], [("A.md", "B.md")]]
)
def test_occupied_and_duplicate_destinations_block_complete_list(moves):
    a = prepare({"A.md": "", "B.md": ""}, moves)
    assert a["status"] == "blocked" and a["writes"] == [] and a["record"] is None


@pytest.mark.parametrize("text", ["[[Missing]]", "[[Same]]", '<a href="A.md">a</a>'])
def test_broken_gains_target_ambiguous_and_unsupported_block(text):
    docs = {"A.md": "", "Ref.md": text, "X/Same.md": "", "Y/Same.md": ""}
    a = prepare(docs, [("A.md", "Missing.md")])
    assert a["status"] == "blocked" and not a["writes"]


def test_duplicate_basename_links_preserved():
    docs = {"A.md": "", "Other/Existing.md": "", "Ref.md": "[[Existing]] [[A]]"}
    a = prepare(docs, [("A.md", "D/Existing.md")])
    assert apply(docs, a)["Ref.md"] == "[[Other/Existing]] [[D/Existing]]"


def test_search_echo_and_final_source_folders():
    server = build_server()
    args = arguments(
        {"A.md": "", "B.md": ""},
        [("A.md", "Deep/Folder/Alpha.md"), ("B.md", "Other/Beta.md")],
    )
    first = invoke(server, args)
    assert "../../Other/Beta.md" in first["search"]
    for extra in [
        dict(searched=False, search=first["search"]),
        dict(searched=True, search=["wrong"]),
    ]:
        a = invoke(server, {**args, **extra})
        assert a["status"] == "texts_needed" and not a["writes"]


@pytest.mark.parametrize(
    "change",
    [
        {"moves": [{"old_path": "../A.md", "path": "B.md"}]},
        {"moves": [{"old_path": "A.md", "path": "B.md", "extra": True}]},
        {"documents": []},
        {"extra": True},
    ],
)
def test_closed_inputs_and_missing_text(change):
    args = arguments({"A.md": ""}, [("A.md", "B.md")])
    result = anyio.run(
        build_server().call_tool, "kb_prepare_document_moves", {**args, **change}
    )
    assert result.is_error
    assert result.structured_content["type"]


def test_row_and_utf8_limits():
    for docs, moves in [
        (
            {f"{i}.md": "" for i in range(1001)},
            [(f"{i}.md", f"D/{i}.md") for i in range(1001)],
        ),
        ({"A.md": "é" * (16 * 1024 * 1024 + 1)}, [("A.md", "B.md")]),
    ]:
        result = anyio.run(
            build_server().call_tool,
            "kb_prepare_document_moves",
            arguments(docs, moves),
        )
        assert result.is_error
        assert result.structured_content["type"].endswith("move-limit-exceeded")


@pytest.mark.parametrize("mode", ["sensitive", "insensitive"])
def test_case_only_rename_and_conservative_collision(mode):
    docs = {"A.md": "[[A]]", "Ref.md": "[[A]]"}
    server = build_server()
    args = arguments(docs, [("A.md", "a.md")], allowed_by=PERMISSION)
    args["case_mode"] = mode
    first = invoke(server, args)
    a = invoke(server, {**args, "searched": True, "search": first["search"]})
    assert apply(docs, a)["Ref.md"] == "[[a]]"
    assert (
        prepare({"A.md": "", "Other.md": ""}, [("A.md", "other.md")])["status"]
        == "blocked"
    )


def test_destination_type_conflict_blocks_complete_list():
    docs = {"A.md": "[[B]]", "B.md": "[[A]]"}
    server = build_server()
    args = arguments(
        docs, [("A.md", "Engineering/A.md"), ("B.md", "D/B.md")], allowed_by=PERMISSION
    )
    args["knowledge_bus_folders"] = [spec("Engineering", "engineering")]
    first = invoke(server, args)
    a = invoke(server, {**args, "searched": True, "search": first["search"]})
    assert a["status"] == "blocked" and not a["writes"]
    assert any(i["code"] == "destination-type-conflict" for i in a["issues"])


def test_prepared_answer_limit(monkeypatch):
    server = build_server()
    args = arguments({"A.md": "[[A]]"}, [("A.md", "B.md")], allowed_by=PERMISSION)
    first = invoke(server, args)
    monkeypatch.setattr(document_move, "MAX_BYTES", 1024)
    result = anyio.run(
        server.call_tool,
        "kb_prepare_document_moves",
        {**args, "searched": True, "search": first["search"]},
    )
    assert result.is_error and result.structured_content["type"].endswith(
        "move-limit-exceeded"
    )
    assert result.structured_content["errors"][0]["pointer"] == "#/documents"


def test_swap_retains_every_entry_field_and_updates_referrer_fingerprint():
    docs = {"A.md": "[[B]]", "B.md": "[[A]]", "Ref.md": "[[A]]"}
    before = {
        p: typed(
            audience=dict(value=p, status="confirmed"), fingerprint=records.digest(t)
        ).model_copy(update={"set_by": "person"})
        for p, t in docs.items()
    }
    server = build_server()
    args = arguments(docs, [("A.md", "B.md"), ("B.md", "A.md")], allowed_by=PERMISSION)
    args["record"] = records.dump(before)
    first = invoke(server, args)
    a = invoke(server, {**args, "searched": True, "search": first["search"]})
    after = apply(docs, a)
    entries = records.parse(a["record"])
    for old, new in [("A.md", "B.md"), ("B.md", "A.md"), ("Ref.md", "Ref.md")]:
        expected = records.plain(before[old])
        expected["fingerprint"] = records.digest(after[new])
        assert records.plain(entries[new]) == expected


@pytest.mark.parametrize(
    "path",
    [
        "A",
        "A.md",
        "./A",
        "../A",
        "/Folder/A",
        "Folder/A",
        "#Heading",
        "a",
        "Same",
        "Same.md",
        "//A",
    ],
)
def test_indexed_resolution_matches_single_move_rules(path):
    paths = ["A.md", "Folder/A.md", "X/Same.md", "Y/Same.md", "other.md"]
    index = document_move.InventoryIndex(set(paths))
    for wiki in [True, False]:
        token = document_move.Token(0, 0, 0, 0, path, wiki)
        assert index.resolve(token, "Folder/Source.md") == document_move._resolve(
            token, "Folder/Source.md", paths
        )


def test_freed_source_name_taken_by_another_row():
    docs = {
        "A.md": "identity:A [[B]]",
        "B.md": "identity:B [[A]]",
        "Ref.md": "[[A]] [[B]]",
    }
    a = prepare(docs, [("A.md", "Freed/Alpha.md"), ("B.md", "A.md")])
    after = apply(docs, a)
    assert after["A.md"] == "identity:B [[Alpha]]"
    assert after["Freed/Alpha.md"] == "identity:A [[A]]"
    assert after["Ref.md"] == "[[Alpha]] [[A]]"


def test_blocked_row_requires_explicit_drop_before_other_row_can_apply():
    docs = {"A.md": "[[B]]", "B.md": "[[A]]", "Stay.md": "unchanged"}
    blocked = prepare(docs, [("A.md", "Chosen.md"), ("B.md", "Stay.md")])
    assert blocked["status"] == "blocked" and not blocked["writes"]
    assert blocked["moves"] == [
        dict(old_path="A.md", path="Chosen.md"),
        dict(old_path="B.md", path="Stay.md"),
    ]
    revised = prepare(docs, [("A.md", "Chosen.md")])
    after = apply(docs, revised)
    assert after["B.md"] == "[[Chosen]]" and after["Stay.md"] == "unchanged"


@pytest.mark.parametrize(
    ("docs", "moves", "blocked"),
    [
        ({"A.md": "", "Block.md": ""}, [("A.md", "Block.md/Child.md")], {"A.md"}),
        (
            {"A.md": "", "B.md": ""},
            [("A.md", "Done.md"), ("B.md", "Done.md/Child.md")],
            {"A.md", "B.md"},
        ),
        ({"A.md": "", "Dir/Stay.md": ""}, [("A.md", "Dir")], {"A.md"}),
        ({"A.md": "", "BLOCK.md": ""}, [("A.md", "block.md/Child.md")], {"A.md"}),
        ({"A.md": "", "Café.md": ""}, [("A.md", "Cafe\u0301.md/Child.md")], {"A.md"}),
    ],
)
def test_final_file_parent_conflicts_block_with_row_identity(docs, moves, blocked):
    answer = prepare(docs, moves)
    assert answer["status"] == "blocked"
    assert answer["writes"] == [] and answer["record"] is answer["digest"] is None
    issues = [i for i in answer["issues"] if i["code"] == "destination-occupied"]
    assert {i["source_path"] for i in issues} == blocked
    for issue in issues:
        assert dict(moves)[issue["source_path"]] in issue["detail"]


def test_collision_diagnostic_names_each_destination_and_occupant():
    answer = prepare(
        {"A.md": "", "B.md": "", "Occupied.md": ""},
        [("A.md", "Free.md"), ("B.md", "Occupied.md")],
    )
    issues = [i for i in answer["issues"] if i["code"] == "destination-occupied"]
    assert answer["status"] == "blocked" and answer["writes"] == []
    assert len(issues) == 1 and issues[0]["source_path"] == "B.md"
    assert "Occupied.md" in issues[0]["detail"] and "B.md" in issues[0]["detail"]
    duplicate = prepare({"A.md": "", "B.md": ""}, [("A.md", "C.md"), ("B.md", "C.md")])
    issues = duplicate["issues"]
    assert {i["source_path"] for i in issues} == {"A.md", "B.md"}
    for issue in issues:
        other = "B.md" if issue["source_path"] == "A.md" else "A.md"
        assert "C.md" in issue["detail"] and other in issue["detail"]


def test_vacated_file_parent_allows_child_destination():
    answer = prepare(
        {"A.md": "", "Block.md": ""},
        [("A.md", "Block.md/Child.md"), ("Block.md", "Gone.md")],
    )
    assert answer["status"] == "ready"


def test_tracking_entry_routes_include_batch_preparation():
    skill = (
        Path(__file__).parents[1] / "skills/kb-track-document-types/SKILL.md"
    ).read_text()
    restriction = skill.split("10. **Keep entries in the document-types file.**", 1)[
        1
    ].split("\n\n", 1)[0]
    assert "`kb_prepare_document_types`" in restriction
    assert "`kb_prepare_document_move`" in restriction
    assert "`kb_prepare_document_moves`" in restriction
