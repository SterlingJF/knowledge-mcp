from __future__ import annotations

import anyio

from knowledge_mcp.main import build_server
from tests.test_conventions_end_to_end import PERMISSION as SAVE
from tests.test_conventions_end_to_end import stored, upsert
from tests.test_document_moves_end_to_end import arguments
from tests.test_filing_end_to_end import PERMISSION

DOCS = {
    "Inbox/retire-evening.md": "# Retire the evening build\n",
    "Inbox/timings-notes.md": "",
    "Index.md": "[[retire-evening]] [[timings-notes]]",
}
MOVES = [
    ("Inbox/retire-evening.md", "Decisions/2026-10-28 retire evening build.md"),
    ("Inbox/timings-notes.md", "Proposals/timings-notes.md"),
]

PLAN = """\
`PROPOSED MOVES` · `Needs your OK`

**2 moves · 1 rename · 1 link repaired · 1 note**

**Moves (2)**

1. `Inbox/retire-evening.md` → Decisions/ as `2026-10-28 retire evening build.md`
2. `Inbox/timings-notes.md` → Proposals/

**Links (1)**

1. `Index.md` · `Inbox/retire-evening.md` → `[[2026-10-28 retire evening build]]`

Waits for you because it moves files and edits links in 1 note. You can undo it afterwards.

Say “Move 2 files” or “Not now”.
"""

CONVENTIONS = """\
`PROPOSED CONVENTIONS` · `Nothing saved`

**Naming and filing for vault**

1. `decision-record` · `Decisions/` · date · title
2. `meeting-notes` · removed

Existing files unchanged until a move.

Say “Save accepted”, which to drop, or “Not now”.
"""


def call(tool, args):
    return anyio.run(build_server().call_tool, tool, args)


def plan(moves, **extra):
    server = build_server()
    args = arguments(DOCS, moves, **extra)
    first = anyio.run(server.call_tool, "kb_prepare_document_moves", args)
    search = first.structured_content["search"]
    args |= {"searched": True, "search": search}
    return anyio.run(server.call_tool, "kb_prepare_document_moves", args)


def test_move_plan_card_names_moves_links_and_what_to_say():
    result = plan(MOVES)

    assert result.structured_content["status"] == "permission_needed"
    assert result.content[0].text == PLAN


def test_blocked_move_plan_card_lists_blockers():
    card = plan([MOVES[0], ("Inbox/timings-notes.md", "Index.md")]).content[0].text

    assert card.startswith("`PROPOSED MOVES` · `Needs your choice`")
    assert "**Blockers (1)**\n\n1. Destination Index.md" in card
    assert card.endswith("Say your choice for each blocker, or “Not now”.\n")


def test_approved_move_plan_card_asks_nothing():
    card = plan(MOVES, allowed_by=PERMISSION).content[0].text

    assert card.startswith("`PROPOSED MOVES` · `Approved`")
    assert "Say" not in card


def test_conventions_card_numbers_each_change():
    date = {"part": "date", "property": "date", "format": "YYYY-MM-DD"}
    decision = upsert() | {
        "name": {"separator": " ", "parts": [date, {"part": "content"}]}
    }
    removal = {
        "change": "remove",
        "universe_spec": decision["universe_spec"],
        "document_type": "meeting-notes",
    }
    result = call(
        "kb_prepare_conventions",
        {
            "location": "unreachable://vault",
            "conventions": stored(upsert() | {"document_type": "meeting-notes"}),
            "changes": [decision, removal],
        },
    )

    assert result.structured_content["status"] == "permission_needed"
    assert result.content[0].text == CONVENTIONS


def test_approved_conventions_card_asks_nothing():
    result = call(
        "kb_prepare_conventions",
        {
            "location": "unreachable://vault",
            "conventions": "",
            "changes": [upsert()],
            "allowed_by": SAVE,
        },
    )

    assert result.content[0].text.startswith("`PROPOSED CONVENTIONS` · `Approved`")
    assert "Say" not in result.content[0].text


def test_text_block_and_structured_card_are_identical():
    moves = plan(MOVES)
    conventions = call(
        "kb_prepare_conventions",
        {"location": "unreachable://vault", "conventions": "", "changes": [upsert()]},
    )

    for result in (moves, conventions):
        assert result.content[0].text == result.structured_content["card"]
