from __future__ import annotations

import anyio

from knowledge_mcp.main import build_server
from tests.test_document_moves_end_to_end import arguments, prepare


def test_card_context_is_echoed():
    docs = {"Inbox/a.md": "x", "Inbox/scan-0412.md": "y"}
    plan = prepare(
        docs,
        [("Inbox/a.md", "Notes/2026-10-28 a.md")],
        summary="File the new files",
        folder="Inbox",
        stays=[dict(path="Inbox/scan-0412.md", reason="no document type")],
        naming=[dict(path="Notes/2026-10-28 a.md", rule="date + title")],
    )
    assert plan["status"] == "ready"
    assert plan["summary"] == "File the new files"
    assert plan["folder"] == "Inbox"
    assert plan["stays"] == [dict(path="Inbox/scan-0412.md", reason="no document type")]
    assert plan["naming"] == [dict(path="Notes/2026-10-28 a.md", rule="date + title")]


def test_card_context_is_absent_when_not_sent():
    plan = prepare({"A.md": "x"}, [("A.md", "B.md")])
    assert not {"summary", "folder", "stays", "naming"} & plan.keys()


def refused(args):
    result = anyio.run(build_server().call_tool, "kb_prepare_document_moves", args)
    assert result.is_error
    return result.structured_content


def test_moved_file_cannot_stay():
    args = arguments(
        {"A.md": "x"}, [("A.md", "B.md")], stays=[dict(path="A.md", reason="r")]
    )
    assert "#/stays/0/path" in str(refused(args))


def test_naming_must_name_a_destination():
    args = arguments(
        {"A.md": "x"}, [("A.md", "B.md")], naming=[dict(path="C.md", rule="r")]
    )
    assert "#/naming/0/path" in str(refused(args))


def test_name_clash_offers_skipping_the_move():
    plan = prepare({"A.md": "x", "B.md": "y"}, [("A.md", "B.md")])
    assert plan["status"] == "blocked"
    clash = next(i for i in plan["issues"] if i["code"] == "destination-occupied")
    assert clash["choices"] == [dict(action="skip_move", path="A.md")]


def test_ambiguous_link_offers_its_candidates():
    docs = {"A.md": "[[Same]]", "x/Same.md": "1", "y/Same.md": "2"}
    plan = prepare(docs, [("A.md", "Moved/A.md")])
    assert plan["status"] == "blocked"
    ambiguous = next(i for i in plan["issues"] if i["code"] == "link-ambiguous")
    assert ambiguous["choices"] == [
        dict(action="bind_link", path="x/Same.md"),
        dict(action="bind_link", path="y/Same.md"),
    ]
