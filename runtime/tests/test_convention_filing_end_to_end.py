from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.harness import PRODUCT
from tests.test_conventions_end_to_end import PERMISSION, PLACE, invoke, stored, upsert
from tests.test_conventions_end_to_end import invoke as configure
from tests.test_document_move_end_to_end import (
    apply,
    arguments,
    prepare,
    vault,
)
from tests.test_document_move_end_to_end import (
    invoke as move,
)
from tests.test_filing_end_to_end import SUBJECT, call, lookup, typed


def values(**extra):
    return dict(
        path=SUBJECT,
        universe_spec=PRODUCT,
        document_type="decision-record",
        properties={"decision_date": "2026-10-18", "project": "Atlas"},
        content="Use a Shared Cache",
        **extra,
    )


def assess(change=None, supplied=None, **extra):
    return lookup(
        [],
        conventions=stored(change or upsert()),
        filing_values=[values() if supplied is None else supplied],
        **extra,
    )["filing"][0]


def test_p01_p02_p05_title_case_and_space():
    paths = [SUBJECT, "Peers/another-decision.md"]
    a = assess(
        entries={path: typed() for path in paths},
        listing=[{"path": path} for path in paths],
    )
    assert a["proposal"] == dict(
        folder="Decisions",
        name="Use a Shared Cache.md",
        path="Decisions/Use a Shared Cache.md",
        folder_new=True,
        name_style="convention",
        evidence=[],
        folder_counts=[],
    )
    assert a["convention"]["file"] == PLACE
    assert a["convention"]["folder"] == ""


def test_all_parts_lower_and_precedence():
    change = upsert()
    change["name"] = {
        "case": "lower",
        "separator": "-",
        "parts": [
            {"part": "document_type"},
            {"part": "date", "property": "decision_date", "format": "YYYY-MM-DD"},
            {"part": "property", "property": "project"},
            {"part": "content"},
        ],
    }
    assert (
        assess(change)["proposal"]["path"]
        == "Decisions/decision-record-2026-10-18-atlas-use-a-shared-cache.md"
    )


def test_date_only_daily_note():
    change = upsert()
    change["folder"] = ["Calendar"]
    change.pop("content")
    change["name"]["parts"] = [
        {"part": "date", "property": "decision_date", "format": "YYYY-MM-DD"}
    ]
    item = values()
    item.pop("content")
    assert assess(change, item)["proposal"]["path"] == "Calendar/2026-10-18.md"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Cache #Plan", "Cache Plan.md"),
        ("Café  Review", "Café Review.md"),
        ("A|B^C:D%%E[F]/G\\H", "ABCDEFGH.md"),
        ("Cache_Plan", "Cache_Plan.md"),
    ],
)
def test_p09_text_conversion(text, expected):
    item = values()
    item["content"] = text
    assert assess(supplied=item)["proposal"]["name"] == expected


def test_p03_p04_no_convention_preserves_b1():
    peers = ["decisions/cache-policy.md", "decisions/queue-policy.md"]
    assert lookup(peers, conventions="")["filing"] == lookup(peers)["filing"]


@pytest.mark.parametrize("missing", ["decision_date", "project", "content"])
def test_p06_missing_values(missing):
    change = upsert()
    change["name"]["parts"] += [
        {"part": "date", "property": "decision_date", "format": "YYYY-MM-DD"},
        {"part": "property", "property": "project"},
    ]
    item = values()
    if missing == "content":
        item.pop(missing)
    else:
        item["properties"].pop(missing)
    a = assess(change, item)
    assert a["status"] == "values_needed"
    assert a["needed"] == [
        {
            "source": "content" if missing == "content" else "property",
            "name": "document title" if missing == "content" else missing,
        }
    ]
    assert a["proposal"] is None


@pytest.mark.parametrize(
    ("date", "fmt", "expected"),
    [
        ("2024-02-29", "YYYY-MM-DD", "2024-02-29"),
        ("2026-10-18", "YYYY-MM", "2026-10"),
        ("2026-10-18", "YYYY", "2026"),
    ],
)
def test_p08_date_formats(date, fmt, expected):
    change = upsert()
    change.pop("content")
    change["name"]["parts"] = [
        {"part": "date", "property": "decision_date", "format": fmt}
    ]
    item = values()
    item["properties"]["decision_date"] = date
    assert assess(change, item)["proposal"]["name"] == expected + ".md"


@pytest.mark.parametrize(
    "mode",
    ["date", "empty", "duplicate", "incompatible", "null-properties", "null-content"],
)
def test_p07_invalid_values(mode):
    change = upsert()
    change["name"]["parts"].append(
        {"part": "date", "property": "decision_date", "format": "YYYY"}
    )
    item = values()
    if mode == "date":
        item["properties"]["decision_date"] = "2026-02-29"
    if mode == "empty":
        item["content"] = "#^[]"
    if mode == "incompatible":
        item["document_type"] = "absent"
    if mode == "null-properties":
        item["properties"] = None
    if mode == "null-content":
        item["content"] = None
    result = anyio.run(
        build_server().call_tool,
        "kb_get_document_type",
        dict(
            location="vault",
            name="Cache Plan.md",
            folders=["inbox"],
            knowledge_bus_folders=[],
            conventions=stored(change),
            filing_values=[item, item] if mode == "duplicate" else [item],
        ),
    )
    assert result.is_error
    assert result.structured_content["type"].endswith("/filing-values-invalid")
    assert result.structured_content["errors"][0]["pointer"].startswith(
        "#/filing_values"
    )


def test_p10_p11_folder_content_reused():
    change = upsert()
    change["folder"] = ["Clients", {"part": "content"}]
    assert (
        assess(change)["proposal"]["path"]
        == "Clients/Use a Shared Cache/Use a Shared Cache.md"
    )


@pytest.mark.parametrize(
    "folder", ["..", "A/B", "A#B", ".knowledge-bus", "node_modules"]
)
def test_p12_unsafe_pattern(folder):
    change = upsert()
    change["folder"] = [folder]
    assert invoke(changes=[change])["type"].endswith("/conventions-invalid")


def test_p13_already_matches_and_extension():
    subject = "Decisions/Use a Shared Cache.MD"
    item = values()
    item["path"] = subject
    a = assess(supplied=item, subject=subject)
    assert a["status"] == "already_matches"
    assert a["convention"]


def test_p14_taken_destination_blocks():
    a = assess(listing=[{"path": SUBJECT}, {"path": "Decisions/Use a Shared Cache.md"}])
    assert a["status"] == "destination_occupied"
    assert a["proposal"] is None
    assert a["convention"]


def test_p15_missing_listing():
    assert assess(listing=False)["status"] == "listing_needed"


def test_p16_descendant_folder_evidence():
    assert not assess(listing=[{"path": "Decisions/old/sub/note.md"}])["proposal"][
        "folder_new"
    ]


def test_p17_p18_candidates_fallback_and_tracking():
    item = values()
    item["path"] = "inbox/Decision Record.md"
    a = lookup(
        [], subject=item["path"], entries={}, conventions=stored(), filing_values=[item]
    )
    selected = [
        f
        for f in a["filing"]
        if f["document_type"] == "decision-record" and f["universe_spec"] == PRODUCT
    ]
    assert selected and selected[0]["proposal"]["name"] == "Use a Shared Cache.md"
    a = call(
        build_server(),
        "kb_prepare_document_types",
        dict(
            location="vault",
            record=records.dump({SUBJECT: typed()}),
            listing=[{"path": SUBJECT}],
            conventions=stored(),
            filing_values=[values()],
        ),
    )
    assert a["filing"][0]["proposal"]["name"] == "Use a Shared Cache.md"


def test_p19_p20_fresh_values_and_configuration():
    item = values()
    item["content"] = "New Title"
    assert assess(supplied=item)["proposal"]["name"] == "New Title.md"
    change = upsert()
    change["folder"] = ["Archive"]
    assert assess(change)["proposal"]["folder"] == "Archive"


def test_p21_peer_conversion_and_p22_order():
    peers = ["decisions/cache-policy.md", "decisions/queue-policy.md"]
    change = upsert()
    change["folder"] = ["decisions"]
    change["name"]["separator"] = "-"
    change["name"]["case"] = "lower"
    item = values()
    item["content"] = "Cache Plan"
    assert (
        assess(change, item)["proposal"]["path"]
        == lookup(peers)["filing"][0]["proposal"]["path"]
    )
    args = dict(conventions=stored(change), filing_values=[item])
    assert (
        lookup(peers, **args)["filing"]
        == lookup(list(reversed(peers)), **args)["filing"]
    )


def test_m01_convention_destination_preserves_independent_link_targets():

    docs = vault()
    item = values()
    item["path"] = "Inbox/Note.md"
    proposed = assess(supplied=item, subject=item["path"])["proposal"]["path"]
    server = build_server()
    args = arguments(docs, path=proposed)
    args["allowed_by"] = {
        "basis": "accepted_change",
        "text": "Move Note.md and repair every referring link.",
    }
    first = move(server, args)
    assert first["status"] == "texts_needed"
    assert first["writes"] == []
    plan = move(
        server,
        {
            **args,
            "documents": [
                {"path": p, "text": t} for p, t in docs.items() if p.endswith(".md")
            ],
            "searched": True,
            "search": first["search"],
        },
    )
    after = apply(docs, plan)
    assert (
        "[plain](../Decisions/Use%20a%20Shared%20Cache.md)"
        in after["References/Index.md"]
    )
    expected = ["References/assets/diagram.png", "Other/Reference.md", "Inbox/Note.md"]
    assert [
        link["target_before"]
        for link in plan["links"]
        if link["source_path"] == "Inbox/Note.md"
    ] == expected
    for link in plan["links"]:
        assert link["target_after"] == (
            proposed if link["target_before"] == item["path"] else link["target_before"]
        )


def test_m02_ambiguous_link_blocks_convention_move():

    docs = vault()
    docs["Other/Reference.md"] = "[[Index]]"
    proposed = assess()["proposal"]["path"]
    plan = prepare(docs, path=proposed)
    assert plan["status"] == "blocked"
    assert plan["writes"] == []
    assert any(i["code"] == "link-ambiguous" for i in plan["issues"])


def test_m04_fresh_convention_requires_new_acceptance_in_skill():

    skill = (
        Path(__file__).parents[1] / "skills/kb-write-document/SKILL.md"
    ).read_text()
    assert "Recheck the conventions digest before applying the proposal." in skill
    assert "renewed acceptance when the destination changes" in skill
    assert "Create accepted missing folders with the move." in skill
    assert "kb_prepare_document_move" in skill
    assert "Get permission covering the complete operation" in skill


def test_m05_m06_configuration_permission_changes_no_documents(tmp_path):

    document = tmp_path / "Note.md"
    document.write_text("# Original\n")
    before = document.read_bytes()
    answer = configure(
        location=str(tmp_path), changes=[upsert()], allowed_by=PERMISSION
    )
    assert answer["status"] == "ready"
    assert document.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Note.md"]
    assert not (tmp_path / PLACE).exists()


def test_p19_p20_same_session_digests_keep_values_fresh():
    server = build_server()
    args = dict(
        location="vault",
        name="Cache Plan.md",
        folders=["inbox"],
        knowledge_bus_folders=[],
        record=records.dump({SUBJECT: typed()}),
        listing=[{"path": SUBJECT}],
        conventions=stored(),
        filing_values=[values()],
    )
    first = call(server, "kb_get_document_type", args)
    digest = first["filing"][0]["convention"]["digest"]
    args.pop("conventions")
    args["conventions_digest"] = digest
    args.pop("filing_values")
    assert (
        call(server, "kb_get_document_type", args)["filing"][0]["status"]
        == "values_needed"
    )
    item = values()
    item["content"] = "Fresh Title"
    args["filing_values"] = [item]
    assert (
        call(server, "kb_get_document_type", args)["filing"][0]["proposal"]["name"]
        == "Fresh Title.md"
    )
    change = upsert()
    change["folder"] = ["Archive"]
    args.pop("conventions_digest")
    args["conventions"] = stored(change)
    assert (
        call(server, "kb_get_document_type", args)["filing"][0]["proposal"]["folder"]
        == "Archive"
    )


def test_p17_exact_candidate_pair_isolation():
    other = upsert()
    other["document_type"] = "design-doc"
    other["folder"] = ["Designs"]
    item = values()
    item["path"] = "inbox/Unknown.md"
    other_value = {**item, "document_type": "design-doc", "content": "Architecture"}
    a = lookup(
        [],
        subject=item["path"],
        entries={},
        conventions=stored(upsert(), other),
        filing_values=[other_value, item],
    )
    proposals = {
        f["document_type"]: f["proposal"] for f in a["filing"] if f.get("convention")
    }
    assert proposals["decision-record"]["path"] == "Decisions/Use a Shared Cache.md"
    assert proposals["design-doc"]["path"] == "Designs/Architecture.md"


@pytest.mark.parametrize(
    "occupied",
    [
        "decisions/Use a Shared Cache.md",
        "Decisions/use a shared cache.MD",
    ],
)
def test_case_equivalent_destination_blocks(occupied):
    a = assess(listing=[{"path": SUBJECT}, {"path": occupied}])
    assert a["status"] == "destination_occupied"
    assert a["proposal"] is None
    assert a["convention"]


def test_case_equivalent_folder_exists():
    a = assess(listing=[{"path": SUBJECT}, {"path": "decisions/old/note.md"}])
    assert a["status"] == "proposed"
    assert a["proposal"]["folder_new"] is False


def test_convention_save_skill_supplies_custom_root_definitions():
    text = (Path(__file__).parents[1] / "skills/kb-write-document/SKILL.md").read_text()
    section = text.split("## Conventions", 1)[1].split(
        "## Names, folders and moves", 1
    )[0]
    assert "`location`" in section
    assert "`knowledge_bus_folders`" in section
    assert "complete local universe spec text" in section
    assert "digest" in section
