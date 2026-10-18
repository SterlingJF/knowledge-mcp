from __future__ import annotations

import anyio
import pytest

from knowledge_mcp import document_types as records
from knowledge_mcp.filing import review_occupancy
from knowledge_mcp.main import build_server
from tests.harness import PRODUCT
from tests.test_conventions_end_to_end import stored, upsert
from tests.test_filing_end_to_end import call, typed


def review(files, folder="Inbox", recursive=False, **extra):
    return call(
        build_server(),
        "kb_prepare_document_types",
        dict(
            location="unreachable://vault",
            record=records.dump(files),
            listing=[dict(path=p) for p in files],
            filing_review=dict(folder=folder, recursive=recursive),
            **extra,
        ),
    )["filing_review"]


@pytest.mark.parametrize("recursive", [False, True])
def test_folder_selection_order_and_unresolved(recursive):
    files = {
        p: typed()
        for p in [
            "Inbox/Z Plan.md",
            "Inbox/A Plan.md",
            "Inbox/Sub/B Plan.md",
            "Decisions/first-note.md",
            "Decisions/second-note.md",
            "Decisions/third-note.md",
            "Decisions/fourth-note.md",
        ]
    }
    a = review(files, recursive=recursive)
    paths = [r["path"] for r in a["assessments"]]
    assert paths == (
        ["Inbox/A Plan.md", "Inbox/Sub/B Plan.md", "Inbox/Z Plan.md"]
        if recursive
        else ["Inbox/A Plan.md", "Inbox/Z Plan.md"]
    )
    assert all(r["proposal"]["path"].startswith("Decisions/") for r in a["assessments"])
    assert review(dict(reversed(list(files.items()))), recursive=recursive) == a


def test_folder_review_requires_explicit_listing():
    result = anyio.run(
        build_server().call_tool,
        "kb_prepare_document_types",
        dict(location="vault", filing_review=dict(folder="")),
    )
    assert result.is_error


def test_provisional_destination_vacated_and_fixed_point():
    def row(old, new):
        return dict(path=old, status="proposed", proposal=dict(path=new))

    rows = [row("A.md", "B.md"), row("B.md", "C.md")]
    review_occupancy(rows, {"A.md", "B.md"})
    assert all(r["status"] == "proposed" for r in rows)
    rows = [row("A.md", "B.md"), row("B.md", "C.md"), row("C.md", "D.md")]
    review_occupancy(rows, {"A.md", "B.md", "C.md", "D.md"})
    assert all(r["status"] == "destination_occupied" for r in rows)
    rows = [row("A.md", "C.md"), row("B.md", "C.md")]
    review_occupancy(rows, {"A.md", "B.md"})
    assert all(r["status"] == "destination_occupied" for r in rows)


def six_notes():
    names = [
        "Inbox/Cache Plan.md",
        "Inbox/Queue Plan.md",
        "Inbox/Kickoff.md",
        "Inbox/Retry Policy.md",
        "Inbox/Scratch.md",
        "Inbox/Unsorted.md",
    ]
    files = {p: typed() for p in names[:2]}
    files[names[2]] = typed().model_copy(update={"document_type": "experiment-plan"})
    files[names[3]] = typed().model_copy(update={"document_type": "risk-assessment"})
    files[names[4]] = typed().model_copy(update={"document_type": "design-doc"})
    for p in ["Policies/retry-limit.md", "Policies/cache-limit.md"]:
        files[p] = files[names[3]]
    changes = []
    for kind, folder in [
        ("decision-record", "Decisions"),
        ("experiment-plan", "Meetings"),
        ("design-doc", "Inbox"),
    ]:
        change = upsert()
        change.update(document_type=kind, folder=[folder])
        if kind == "decision-record":
            change["name"] = dict(
                case="lower", separator="-", parts=[dict(part="content")]
            )
        elif kind == "experiment-plan":
            change["name"]["parts"].insert(
                0, dict(part="date", property="meeting_date", format="YYYY-MM-DD")
            )
        changes.append(change)
    values = [
        dict(
            path=p,
            universe_spec=PRODUCT,
            document_type=files[p].document_type,
            content=p.split("/")[-1][:-3],
            **(
                dict(properties=dict(meeting_date="2026-10-18"))
                if p == names[2]
                else {}
            ),
        )
        for p in [*names[:3], names[4]]
    ]
    return names, files, stored(*changes), values


def test_six_note_example_mixed_evidence_and_new_folders():
    names, files, conventions, values = six_notes()
    a = call(
        build_server(),
        "kb_prepare_document_types",
        dict(
            location="unreachable://vault",
            record=records.dump(files),
            listing=[dict(path=p) for p in [*files, names[5]]],
            filing_review=dict(folder="Inbox"),
            conventions=conventions,
            filing_values=values,
        ),
    )["filing_review"]
    proposed = [r for r in a["assessments"] if r["status"] == "proposed"]
    assert len(proposed) == 4
    assert {r["path"]: r["proposal"]["path"] for r in proposed} == dict(
        zip(
            names[:4],
            [
                "Decisions/cache-plan.md",
                "Decisions/queue-plan.md",
                "Meetings/2026-10-18 Kickoff.md",
                "Policies/retry-policy.md",
            ],
            strict=True,
        )
    )
    assert [
        r["path"] for r in a["assessments"] if r["status"] == "already_matches"
    ] == [names[4]]
    assert names[5] in {r["path"] for r in a["unresolved"]}
    assert all(r["proposal"]["folder_new"] for r in proposed if r["path"] != names[3])
    retry = next(r for r in proposed if r["path"] == names[3])
    assert "convention" not in retry and len(retry["proposal"]["evidence"]) == 2
    assert all("convention" in r for r in proposed if r is not retry)
    assert all(r["values"]["content"] for r in proposed if r is not retry)


def test_missing_values_stay_unresolved():
    names, files, conventions, _ = six_notes()
    a = review(files, conventions=conventions)
    assert names[0] in {r["path"] for r in a["unresolved"]}
    row = next(r for r in a["assessments"] if r["path"] == names[0])
    assert row["status"] == "values_needed" and row["proposal"] is None


def test_mcp_provisional_chain_keeps_snapshot_and_saved_convention():
    files = {p: typed() for p in ["A.md", "B.md"]}
    change = upsert()
    change["folder"] = []
    conventions = stored(change)
    values = [
        dict(
            path=p, universe_spec=PRODUCT, document_type="decision-record", content=name
        )
        for p, name in [("A.md", "B"), ("B.md", "C")]
    ]
    a = review(files, folder="", conventions=conventions, filing_values=values)
    assert [r["proposal"]["path"] for r in a["assessments"]] == ["B.md", "C.md"]
    assert all(r["convention"]["definition"]["folder"] == [] for r in a["assessments"])


@pytest.mark.parametrize(
    ("moves", "paths", "blocked"),
    [
        ({"A.md": "Block.md/Child.md"}, {"A.md", "Block.md"}, {"A.md"}),
        (
            {"A.md": "Done.md", "B.md": "Done.md/Child.md"},
            {"A.md", "B.md"},
            {"A.md", "B.md"},
        ),
        ({"A.md": "Dir"}, {"A.md", "Dir/Stay.md"}, {"A.md"}),
        ({"A.md": "block.md/Child.md"}, {"A.md", "BLOCK.md"}, {"A.md"}),
        ({"A.md": "Cafe\u0301.md/Child.md"}, {"A.md", "Café.md"}, {"A.md"}),
        (
            {"A.md": "Block.md/Child.md", "Block.md": "Gone.md"},
            {"A.md", "Block.md"},
            set(),
        ),
        (
            {"A.md": "B.md", "B.md": "Block.md/Child.md"},
            {"A.md", "B.md", "Block.md"},
            {"A.md", "B.md"},
        ),
    ],
)
def test_review_file_parent_conflicts_and_vacated_parents(moves, paths, blocked):
    rows = [
        dict(path=old, status="proposed", proposal=dict(path=new))
        for old, new in moves.items()
    ]
    review_occupancy(rows, paths)
    assert {r["path"] for r in rows if r["status"] == "destination_occupied"} == blocked
    assert all(r["proposal"] is None for r in rows if r["path"] in blocked)
