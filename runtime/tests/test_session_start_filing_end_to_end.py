from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import anyio
import pytest
from jsonschema import Draft202012Validator

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.document_types_harness import Harness, KnowledgeBase, fingerprint
from tests.harness import BUNDLED, PRODUCT, checked, header, server_parameters, session
from tests.test_conventions_end_to_end import stored, upsert
from tests.test_document_moves_end_to_end import apply
from tests.test_filing_end_to_end import PERMISSION, typed

UNIVERSE = "session-notes"
ARRIVALS = ["Inbox/Cache Plan.md", "Inbox/Kickoff.md", "Inbox/Loose thoughts.md"]
OLD = "Meetings/Review.md"
MOVED = "Inbox/Review.md"
DELETED = "Notes/Old checklist.md"
PEERS = ["Calendar/first-meeting.md", "Calendar/second-meeting.md"]
SKILL = Path(__file__).parents[1] / "skills/kb-track-document-types/SKILL.md"


def configuration():
    text = (BUNDLED / PRODUCT / "universe.kbp.yaml").read_text()
    text = text.replace(PRODUCT, UNIVERSE).replace("experiment-plan", "meeting-note")
    return [
        dict(folder="", files=[dict(name="notes.kbp.yaml", **header(text), text=text)])
    ]


def saved(kind="meeting-note", **extra):
    return typed().model_copy(
        update=dict(universe_spec=UNIVERSE, document_type=kind, **extra)
    )


def convention():
    change = upsert()
    change["universe_spec"] = UNIVERSE
    change["name"] = dict(case="lower", separator="-", parts=[dict(part="content")])
    return stored(change)


def inputs(**extra):
    return dict(
        location="unreachable://session-notes",
        record="",
        knowledge_bus_folders=configuration(),
        conventions=convention(),
        **extra,
    )


async def ask(client, arguments):
    tool = next(
        t
        for t in (await client.list_tools()).tools
        if t.name == "kb_prepare_document_types"
    )
    result = await client.call_tool(tool.name, arguments)
    answer = checked(result, "document-types-update")
    Draft202012Validator(tool.output_schema).validate(answer)
    return answer


def update(server=None, **extra):
    args = inputs()
    args.update(extra)
    result = anyio.run(
        (server or build_server()).call_tool, "kb_prepare_document_types", args
    )
    return checked(result, "document-types-update")


def five_events():
    files = {
        OLD: saved(
            set_by="person",
            audience=records.Audience(value="the team lead", status="confirmed"),
            fingerprint=fingerprint("review"),
        ),
        DELETED: saved(fingerprint=fingerprint("old checklist")),
        **{p: saved(fingerprint=fingerprint(p)) for p in PEERS},
    }
    listing = [
        dict(path=p, fingerprint=fingerprint("review" if p == MOVED else p))
        for p in [*ARRIVALS, MOVED, *PEERS]
    ]
    entries = [
        dict(
            path=ARRIVALS[0],
            set_by="agent",
            universe_spec=UNIVERSE,
            document_type="decision-record",
        ),
        dict(
            path=ARRIVALS[1],
            set_by="agent",
            universe_spec=UNIVERSE,
            document_type="meeting-note",
        ),
        dict(path=ARRIVALS[2], set_by="agent", no_document_type=True),
    ]
    values = [
        dict(
            path=ARRIVALS[0],
            universe_spec=UNIVERSE,
            document_type="decision-record",
            content="Cache Plan",
        )
    ]
    return dict(
        record=records.dump(files),
        listing=listing,
        entries=entries,
        filing_values=values,
        allowed_by=PERMISSION,
    )


def proposals(answer):
    relevant = {
        e["path"]
        for e in answer.get("listing_changes", [])
        if e["change"] in {"created", "moved"}
    }
    return {
        a["path"]: a["proposal"]["path"]
        for a in answer["filing"]
        if a["status"] == "proposed"
        and ("listing_changes" not in answer or a["path"] in relevant)
    }


@pytest.mark.parametrize("local", [False, True], ids=["content-only", "local"])
def test_five_events_fresh_process_and_second_session(tmp_path, local):
    base = KnowledgeBase(tmp_path / "vault" if local else None)
    initial = five_events()
    base.write(
        ".knowledge-bus/plugins/knowledge-mcp/document-types.yaml", initial["record"]
    )
    for item in initial["listing"]:
        base.write(item["path"], "review" if item["path"] == MOVED else item["path"])
    harness = Harness(base)
    initial["listing"] = harness.listing()
    args = inputs()
    args.update(initial, location=base.location)

    async def first(client):
        answer = await ask(client, args)
        assert Counter(e["change"] for e in answer["listing_changes"]) == dict(
            created=3, moved=1, deleted=1
        )
        assert proposals(answer) == {
            ARRIVALS[0]: "Decisions/cache-plan.md",
            ARRIVALS[1]: "Calendar/kickoff.md",
            MOVED: "Calendar/review.md",
        }
        assert {c["path"] for c in answer["changed"] if c["change"] == "deleted"} == {
            DELETED
        }
        saved_files = records.parse(answer["record"])
        assert saved_files[MOVED] == records.parse(args["record"])[OLD]
        assert OLD not in saved_files and DELETED not in saved_files
        return answer

    first_answer = session(server_parameters(tmp_path / "first"), first)
    harness.write_record(first_answer["record"])

    async def second(client):
        args.update(record=harness.record())
        args.pop("entries")
        answer = await ask(client, args)
        assert answer["listing_changes"] == []
        assert answer["to_settle"] == []
        assert records.parse(harness.record())[ARRIVALS[2]].no_document_type
        assert (
            next(a for a in answer["filing"] if a["path"] == ARRIVALS[2])["status"]
            == "no_document_type"
        )

    session(server_parameters(tmp_path / "second"), second)


def test_without_save_permission_keeps_events_and_assessments():
    args = five_events()
    args.pop("allowed_by")
    answer = update(**args)
    assert answer["record"] is answer["digest"] is None
    assert len(answer["listing_changes"]) == 5
    assert set(proposals(answer)) == {ARRIVALS[0], ARRIVALS[1], MOVED}


def test_classification_and_value_followups_retain_agent_report():
    server = build_server()
    args = five_events()
    entries, values = args.pop("entries"), args.pop("filing_values")
    first = update(server, **args)
    observed = json.loads(json.dumps(first["listing_changes"]))
    followup = update(
        server, record=first["record"], entries=entries, allowed_by=PERMISSION
    )
    assert "listing_changes" not in followup
    instructions = SKILL.read_text()
    assert re.search(
        r"Follow-up (?:answers|responses) can omit `listing_changes`", instructions
    )
    assert "Follow-up calls can omit `listing_changes`" not in instructions
    final = update(server, record=followup["record"], filing_values=values)
    assert proposals(final)[ARRIVALS[0]] == "Decisions/cache-plan.md"
    assert Counter(e["change"] for e in observed) == dict(created=3, moved=1, deleted=1)


@pytest.mark.parametrize(
    "status", ["values_needed", "already_matches", "no_peers", "destination_occupied"]
)
def test_typed_arrival_always_has_assessment(status):
    args = five_events()
    if status == "values_needed":
        args.pop("filing_values")
    elif status == "already_matches":
        args["listing"][0]["path"] = "Decisions/cache-plan.md"
        args["entries"][0]["path"] = "Decisions/cache-plan.md"
        args["filing_values"][0]["path"] = "Decisions/cache-plan.md"
    elif status == "no_peers":
        args["conventions"] = ""
        args["record"] = ""
        args.pop("filing_values")
    else:
        args["listing"].append(dict(path="Decisions/cache-plan.md"))
    answer = update(**args)
    row = next(a for a in answer["filing"] if a["path"] == args["entries"][0]["path"])
    assert row["status"] == status
    assert row["proposal"] is None
    if status == "values_needed":
        assert row["needed"] == [dict(source="content", name="document title")]


@pytest.mark.parametrize(
    "part",
    [
        dict(part="date", property="meeting_date", format="YYYY-MM-DD"),
        dict(part="property", property="record_number"),
    ],
)
def test_missing_recorded_date_or_number_stays_a_question(part):
    change = upsert()
    change["universe_spec"] = UNIVERSE
    change["name"]["parts"].insert(0, part)
    args = five_events()
    args["conventions"] = stored(change)
    row = next(a for a in update(**args)["filing"] if a["path"] == ARRIVALS[0])
    assert row["status"] == "values_needed" and row["proposal"] is None
    assert row["needed"] == [dict(source="property", name=part["property"])]


def test_server_uses_supplied_text_without_reading_knowledge_base(
    tmp_path, monkeypatch
):
    original = Path.open
    base = tmp_path / "unopened-vault"

    def guarded(path, *args, **kwargs):
        assert not path.is_relative_to(base), f"Server accessed {path}"
        return original(path, *args, **kwargs)

    args = five_events()
    monkeypatch.setattr(Path, "open", guarded)
    answer = update(location=str(base), **args)
    assert len(answer["listing_changes"]) == 5


@pytest.mark.parametrize("many", [False, True], ids=["single", "list"])
def test_accepted_session_proposals_preserve_supported_links(many):
    answer = update(**five_events())
    moves = list(proposals(answer).items())[: 2 if many else 1]
    old, new = moves[0]
    docs = {p: "# Heading\nBlock ^id\n" for p in [*ARRIVALS, MOVED, *PEERS]}
    docs["Index.md"] = (
        f"[[{old[:-3]}#Heading|Title]] ![[{old[:-3]}#^id]] [Note](Inbox/Cache%20Plan.md#Heading)"
    )
    server = build_server()
    args = dict(
        location="unreachable://session-notes",
        record=answer["record"],
        knowledge_bus_folders=configuration(),
        listing=[dict(path=p) for p in docs],
        documents=[dict(path=p, text=t) for p, t in docs.items()],
        allowed_by=PERMISSION,
        case_mode="sensitive",
    )
    tool = "kb_prepare_document_moves" if many else "kb_prepare_document_move"
    args.update(
        dict(moves=[dict(old_path=a, path=b) for a, b in moves])
        if many
        else dict(old_path=old, path=new)
    )
    needed = anyio.run(server.call_tool, tool, args).structured_content
    assert needed["status"] == "texts_needed"
    plan = checked(
        anyio.run(
            server.call_tool, tool, dict(args, searched=True, search=needed["search"])
        ),
        "document-moves" if many else "document-move",
    )
    after = apply(docs, plan)
    assert (
        after["Index.md"]
        == "[[Decisions/cache-plan#Heading|Title]] ![[Decisions/cache-plan#^id]] [Note](Decisions/cache-plan.md#Heading)"
    )
    saved_files = records.parse(plan["record"])
    for old, new in moves:
        assert (
            saved_files[new].document_type
            == records.parse(answer["record"])[old].document_type
        )
        assert old not in saved_files


def test_several_candidate_types_have_no_selected_proposal():
    answer = update(listing=[dict(path="Inbox/Notes.md")])
    assert len(answer["filing"]) > 1
    assert len({(a["universe_spec"], a["document_type"]) for a in answer["filing"]}) > 1
    assert answer["to_settle"][0]["path"] == "Inbox/Notes.md"
    assert all(c["change"] != "settled" for c in answer["changed"])


def test_preview_cap_keeps_complete_events_counts_and_assessments():
    paths = [f"Inbox/Note-{i:02}.md" for i in range(73)]
    answer = update(
        listing=[dict(path=p) for p in reversed(paths)],
        entries=[
            dict(
                path=p,
                set_by="agent",
                universe_spec=UNIVERSE,
                document_type="meeting-note",
            )
            for p in paths
        ],
        allowed_by=PERMISSION,
    )
    assert Counter(e["change"] for e in answer["listing_changes"]) == dict(created=73)
    assert len(answer["changed"]) == len(answer["filing"]) == 73
    assert len(records.parse(answer["record"])) == 73
    ordered = sorted({e["path"] for e in answer["listing_changes"]})
    assert ordered[:50] == paths[:50]
    assert len(ordered) - len(ordered[:50]) == 23


@pytest.mark.parametrize("reverse", [False, True])
def test_inventory_permutations_preserve_group_contents_and_assessment_order(reverse):
    args = five_events()
    if reverse:
        args["listing"].reverse()
        args["entries"].reverse()
    answer = update(**args)
    groups = {
        kind: sorted(
            e["path"] for e in answer["listing_changes"] if e["change"] == kind
        )
        for kind in ("created", "moved", "deleted")
    }
    assert groups == dict(created=ARRIVALS, moved=[MOVED], deleted=[DELETED])
    assert [a["path"] for a in answer["filing"]] == sorted(
        a["path"] for a in answer["filing"]
    )


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ({"a/Note.md": "a"}, {"b/Note.md": "b"}, {"created": 1, "deleted": 1}),
        ({"a/Note.md": None}, {"b/Note.md": None}, {"moved": 1}),
        ({"a/A.md": "a", "a/B.md": "a"}, {"b/C.md": "a"}, {"created": 1, "deleted": 2}),
        ({"a/Note.md": "a"}, {"a/Note.md": "b"}, {"edited": 1}),
        ({"a/Note.md": None}, {"a/Note.md": "a"}, {"edited": 1}),
    ],
)
def test_comparison_boundaries_preserve_classification(before, after, expected):
    files = {
        p: saved(fingerprint=fingerprint(f) if f else None) for p, f in before.items()
    }
    answer = update(
        record=records.dump(files),
        listing=[
            dict(path=p, fingerprint=fingerprint(f) if f else None)
            for p, f in after.items()
        ],
        allowed_by=PERMISSION,
    )
    assert Counter(e["change"] for e in answer["listing_changes"]) == expected
    for entry in records.parse(answer["record"] or records.dump(files)).values():
        assert entry.document_type == "meeting-note"
        assert entry.time == next(iter(files.values())).time


def test_nested_configuration_files_are_excluded_from_events():
    answer = update(
        listing=[dict(path="Team/.knowledge-bus/kbp.yaml"), dict(path="Inbox/New.md")]
    )
    assert answer["listing_changes"] == [dict(change="created", path="Inbox/New.md")]


def test_destination_conflict_preserves_original_entry():
    args = five_events()
    nested = configuration()[0]
    nested["folder"] = "Inbox"
    nested["files"][0]["text"] = nested["files"][0]["text"].replace(
        UNIVERSE, "other-notes"
    )
    nested["files"][0]["id"] = "other-notes"
    args["knowledge_bus_folders"] = [*configuration(), nested]
    answer = update(
        **{k: v for k, v in args.items() if k not in {"entries", "filing_values"}}
    )
    files = records.parse(answer["record"])
    assert files[OLD] == records.parse(args["record"])[OLD]
    assert MOVED not in files
    assert MOVED in {r["path"] for r in answer["to_settle"]}


def test_concurrent_merge_replays_events_without_stale_inventory():
    args = five_events()
    first = update(**args)
    fresh = records.parse(args["record"])
    fresh["Elsewhere/Concurrent.md"] = saved()
    replay = update(
        record=records.dump(fresh),
        changes=first["listing_changes"],
        entries=args["entries"],
        allowed_by=PERMISSION,
    )
    files = records.parse(replay["record"])
    assert "Elsewhere/Concurrent.md" in files
    assert MOVED in files and OLD not in files and DELETED not in files


@pytest.mark.parametrize(
    ("extra", "pointer"),
    [
        (
            {"listing": [{"path": "Note.md", "unexpected": True}]},
            "#/listing/0/unexpected",
        ),
        (
            {"changes": [{"change": "moved", "path": "Note.md"}]},
            "#/changes/0/FileMoved/old_path",
        ),
        (
            {
                "filing_values": [
                    {
                        "path": "Note.md",
                        "universe_spec": UNIVERSE,
                        "document_type": "meeting-note",
                        "unexpected": True,
                    }
                ]
            },
            "#/filing_values/0/unexpected",
        ),
        ({"unexpected": True}, "#/unexpected"),
    ],
)
def test_closed_inputs_return_precise_structured_errors(extra, pointer):
    result = anyio.run(
        build_server().call_tool, "kb_prepare_document_types", inputs(**extra)
    )
    assert result.is_error
    assert pointer in {e["pointer"] for e in result.structured_content["errors"]}


@pytest.mark.parametrize(
    "pattern",
    [
        r"incomplete.*listing|listing.*incomplete",
        r"50 distinct files",
        r"full counts|complete counts",
        r"omitted",
        r"current path.*universe spec.*document type",
        r"no_document_type.*current listing|current listing.*no_document_type",
        r"fingerprint.*counts",
        r"external.*repair|repair.*external",
        r"first.*fingerprint|fingerprint.*baseline",
        r"Unicode code.point",
        r"candidate.*conditional|conditional.*candidate",
    ],
)
def test_session_start_skill_covers_agent_only_boundaries(pattern):
    assert re.search(pattern, SKILL.read_text(), re.IGNORECASE | re.DOTALL)
