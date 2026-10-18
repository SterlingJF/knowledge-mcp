from __future__ import annotations

import anyio
import pytest

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.harness import BUNDLED, CODEBASE, PRODUCT, header

SUBJECT = "inbox/Cache Plan.md"
PERMISSION = {"basis": "request", "text": "Keep these document types."}


def typed(**extra):
    return records.entry(
        universe_spec=PRODUCT,
        version="1",
        document_type="decision-record",
        set_by="agent",
        allowed_by=PERMISSION,
        time="2026-10-18T00:00:00Z",
        **extra,
    )


def call(server, name, arguments):
    result = anyio.run(server.call_tool, name, arguments)
    assert not result.is_error, result.structured_content
    return result.structured_content


def lookup(peers, *, subject=SUBJECT, listing=True, entries=None, **extra):
    files = entries if entries is not None else {p: typed() for p in [subject, *peers]}
    folder, _, name = subject.rpartition("/")
    arguments = dict(
        location="unreachable://vault",
        name=name,
        folders=folder.split("/") if folder else [],
        knowledge_bus_folders=[],
        record=records.dump(files),
    )
    if listing:
        arguments["listing"] = (
            [{"path": p} for p in [subject, *peers]] if listing is True else listing
        )
    arguments.update(extra)
    return call(build_server(), "kb_get_document_type", arguments)


def assessment(peers, **kwargs):
    return lookup(peers, **kwargs)["filing"][0]


def test_p01_majority():
    a = assessment(
        [
            "decisions/cache-policy.md",
            "decisions/queue-policy.md",
            "archive/retry-policy.md",
        ]
    )
    assert a["proposal"] == dict(
        folder="decisions",
        name="cache-plan.md",
        path="decisions/cache-plan.md",
        folder_new=False,
        name_style="lower-kebab",
        evidence=["decisions/cache-policy.md", "decisions/queue-policy.md"],
        folder_counts=[
            {"folder": "archive", "count": 1},
            {"folder": "decisions", "count": 2},
        ],
    )


@pytest.mark.parametrize(
    ("peers", "subject", "folder"),
    [
        (["inbox/a.md", "other/b.md"], SUBJECT, "inbox"),
        (["team/decisions/a.md", "other/b.md"], "team/inbox/Note.md", "team/decisions"),
        (["z/a.md", "a/b.md"], SUBJECT, "a"),
    ],
)
def test_p02_p04_ties(peers, subject, folder):
    a = assessment(peers, subject=subject)
    assert (
        a["proposal"]["folder"] if a["proposal"] else subject.rpartition("/")[0]
    ) == folder


@pytest.mark.parametrize(
    ("peers", "name"),
    [
        (["d/first-note.md", "d/second-note.md"], "cache-plan.md"),
        (["d/first_note.md", "d/second_note.md"], "cache_plan.md"),
        (["d/first-note.md"], "Cache Plan.md"),
        (["d/first.md", "d/second.md"], "Cache Plan.md"),
        (
            [
                "d/first-note.md",
                "d/second-note.md",
                "d/third_note.md",
                "d/fourth_note.md",
            ],
            "Cache Plan.md",
        ),
    ],
)
def test_p05_p06_styles(peers, name):
    assert assessment(peers)["proposal"]["name"] == name


@pytest.mark.parametrize("name", ["Café Plan.md", "Cache & Plan.md"])
def test_p07_unsupported_name(name):
    assert (
        assessment(["d/first-note.md", "d/second-note.md"], subject="inbox/" + name)[
            "proposal"
        ]["name"]
        == name
    )


def test_p08_no_peers():
    assert assessment([])["status"] == "no_peers"


def test_p09_untyped():
    entry = records.entry(
        no_document_type=True,
        set_by="agent",
        allowed_by=PERMISSION,
        time="2026-10-18T00:00:00Z",
    )
    assert assessment([], entries={SUBJECT: entry})["status"] == "no_document_type"


def test_p10_p18_candidates_and_fallback():
    a = lookup([], entries={})
    expected = {(c["universe_spec"], c["document_type"]) for c in a["candidates"]}
    expected |= {
        (g["universe_spec"], k["document_type"])
        for g in a["every_document_type"] or []
        for k in g["kinds"]
    }
    assert {(f["universe_spec"], f["document_type"]) for f in a["filing"]} == expected


def test_p11_already_matches():
    assert (
        assessment(["d/first-note.md", "d/second-note.md"], subject="d/cache-plan.md")[
            "status"
        ]
        == "already_matches"
    )


def test_p12_occupied():
    peers = ["d/first-note.md", "d/second-note.md"]
    a = assessment(
        peers, listing=[{"path": p} for p in [SUBJECT, *peers, "d/cache-plan.md"]]
    )
    assert a["status"] == "destination_occupied"
    assert a["proposal"] is None


def test_p13_stale():
    assert (
        assessment([], entries={p: typed() for p in [SUBJECT, "deleted/a.md"]})[
            "status"
        ]
        == "no_peers"
    )


def test_p14_pending_changes():
    a = assessment(
        ["new/a.md"],
        entries={p: typed() for p in [SUBJECT, "old/a.md", "old/b.md"]},
        changes=[
            {"change": "moved", "old_path": "old/a.md", "path": "new/a.md"},
            {"change": "deleted", "path": "old/b.md"},
        ],
    )
    assert a["proposal"]["evidence"] == ["new/a.md"]


def test_p15_team_boundary():
    a = assessment(
        ["team/a.md"],
        knowledge_bus_folders=[
            {
                "folder": "team",
                "files": [
                    {"name": p.name, **header(p.read_text())}
                    for p in sorted((BUNDLED / CODEBASE).glob("*.kbp.yaml"))
                ],
            }
        ],
    )
    assert a["status"] == "no_peers"


def test_p16_missing_listing():
    assert assessment([], listing=False)["status"] == "listing_needed"


def test_p17_missing_peer_definitions():
    a = assessment(
        ["team/a.md"],
        listing=[
            {"path": SUBJECT},
            {"path": "team/a.md"},
            {"path": "team/.knowledge-bus/team.kbp.yaml"},
        ],
    )
    assert a["status"] == "evidence_incomplete"


def test_p19_digest_and_p20_order():
    server = build_server()
    files = {p: typed() for p in [SUBJECT, "d/first-note.md", "d/second-note.md"]}
    args = dict(
        location="vault",
        folders=["inbox"],
        name="Cache Plan.md",
        knowledge_bus_folders=[],
        record=records.dump(files),
        listing=[{"path": p} for p in files],
    )
    first = call(server, "kb_get_document_type", args)
    digest = next(r["digest"] for r in first["received"] if r["name"] == records.PLACE)
    del args["record"]
    args.update(record_digest=digest, listing=list(reversed(args["listing"])))
    assert call(server, "kb_get_document_type", args)["filing"] == first["filing"]


def test_p18_tracking():
    files = {p: typed() for p in [SUBJECT, "d/first-note.md", "d/second-note.md"]}
    a = call(
        build_server(),
        "kb_prepare_document_types",
        dict(
            location="vault",
            record=records.dump(files),
            listing=[{"path": p} for p in files],
        ),
    )
    assert {f["path"] for f in a["filing"]} == set(files)
