from __future__ import annotations

import anyio

from knowledge_mcp.main import build_server
from knowledge_mcp.views import markdown
from tests.test_document_moves_end_to_end import arguments, prepare

INDEX = "# Index\n\nSee\n[[retire-evening]] and [label](retire-evening.md)\n"


def _links():
    docs = {"decisions-index.md": INDEX, "retire-evening.md": "x"}
    plan = prepare(docs, [("retire-evening.md", "2026-10-28 retire evening build.md")])
    assert plan["status"] == "ready", plan["issues"]
    return plan


def test_wiki_link_carries_line_and_text():
    wiki = _links()["links"][0]
    assert wiki["line"] == 4
    assert wiki["text"] == "[[retire-evening]]"


def test_markdown_link_carries_line_and_text():
    md = _links()["links"][1]
    assert md["line"] == 4
    assert md["text"] == "[label](retire-evening.md)"


def test_link_on_line_one():
    docs = {"A.md": "[[B]]\n", "B.md": "x"}
    link = prepare(docs, [("B.md", "C.md")])["links"][0]
    assert (link["line"], link["text"]) == (1, "[[B]]")


def test_absent_without_texts():
    args = arguments({"A.md": "[[B]]", "B.md": "x"}, [("B.md", "C.md")])
    result = anyio.run(build_server().call_tool, "kb_prepare_document_moves", args)
    plan = result.structured_content
    assert plan["status"] == "texts_needed"
    assert plan["links"] == []


def test_card_shows_note_line_and_tokens():
    card = _links()["card"]
    assert (
        "`decisions-index.md:4` · `[[retire-evening]]` → "
        "`[[2026-10-28 retire evening build]]`" in card
    )


def test_card_renders_without_details():
    link = dict(
        source_path="A.md",
        start=0,
        end=5,
        target_before="B.md",
        target_after="C.md",
        replacement="[[C]]",
    )
    assert markdown._link(link) == "`A.md` · `B.md` → `[[C]]`"


def test_ambiguous_link_issue_carries_line_and_text():
    docs = {"weekly.md": "x\n[[proposal]]", "a/proposal.md": "1", "b/proposal.md": "2"}
    plan = prepare(docs, [("weekly.md", "Moved/weekly.md")])
    found = next(i for i in plan["issues"] if i["code"] == "link-ambiguous")
    assert (found["line"], found["text"]) == (2, "[[proposal]]")
