from __future__ import annotations

import json

from knowledge_mcp.views.markdown import PLACE
from tests.harness import server_parameters, session

# The proposal card from the demo (docs/images/km-still-1-proposal.png).
DEMO = {
    "location": "~/notes/cache-policy.md",
    "summary": "Focus proposal on retiring the evening build",
    "rows": [
        {
            "current": {"label": "Title", "text": "Build schedule and cache rollout"},
            "proposed": {"label": "Title", "text": "Evening build retirement"},
            "mark": "suggested",
            "sources": [{"file": "meeting-notes.md", "line_number": 15}],
        },
        {
            "current": {
                "label": "Motivation",
                "text": "evening build never finishes",
            },
            "proposed": {
                "label": "Motivation",
                "text": "7 of 9 evening runs hit the 6-hour limit",
            },
            "mark": "supported",
            "sources": [{"file": "build-timings.xlsx", "place": "Evening!A2:D10"}],
        },
        {
            "proposed": {
                "label": "Status",
                "text": "Proposed. Approval is disputed.",
            },
            "mark": "conflicting",
            "sources": [
                {"file": "cache-rollout-review.pptx", "place": "slide 7"},
                {"file": "meeting-notes.md", "line_number": 11},
                {"file": "meeting-notes.md", "line_number": 19},
            ],
        },
        {
            "current": {
                "label": "Open question",
                "text": "what baseline would show build times doubled?",
            },
            "proposed": {
                "label": "Still open",
                "text": "no timings from before the cache",
            },
            "mark": "partly",
            "sources": [
                {"file": "build-timings.xlsx", "place": "Evening!A2"},
                {"file": "meeting-notes.md", "line_number": 21},
            ],
        },
    ],
    "left_out": [
        {
            "file": "vendor-quote.xlsx",
            "reason": "answers none of this proposal's questions",
        }
    ],
}

TABLE = f"""\
`PROPOSED CHANGES` · `Nothing saved`

**Focus proposal on retiring the evening build**

| ID | Current | Proposed | Source |
| --- | --- | --- | --- |
| C1 | **Title:** Build schedule and cache rollout | ◆ Suggested · **Title:** Evening build retirement | `meeting-notes.md:15` |
| C2 | **Motivation:** evening build never finishes | ● Supported · **Motivation:** 7 of 9 evening runs hit the 6-hour limit | `build-timings.xlsx{PLACE}Evening!A2:D10` |
| C3 | — | ✕ Conflicting · **Status:** Proposed. Approval is disputed. | `cache-rollout-review.pptx{PLACE}slide 7` · `meeting-notes.md:11` · `meeting-notes.md:19` |
| C4 | **Open question:** what baseline would show build times doubled? | ◐ Partly answered · **Still open:** no timings from before the cache | `build-timings.xlsx{PLACE}Evening!A2` · `meeting-notes.md:21` |

⊘ `vendor-quote.xlsx` left out: answers none of this proposal's questions
"""


LIST = f"""\
`PROPOSED CHANGES` · `Nothing saved`

**Focus proposal on retiring the evening build**

**C1** · ◆ Suggested · **Title**

- Now: Build schedule and cache rollout
- Proposed: Evening build retirement
- `meeting-notes.md:15`

**C2** · ● Supported · **Motivation**

- Now: evening build never finishes
- Proposed: 7 of 9 evening runs hit the 6-hour limit
- `build-timings.xlsx{PLACE}Evening!A2:D10`

**C3** · ✕ Conflicting · **Status**

- Now: —
- Proposed: Proposed. Approval is disputed.
- `cache-rollout-review.pptx{PLACE}slide 7` · `meeting-notes.md:11` · `meeting-notes.md:19`

**C4** · ◐ Partly answered · **Still open**

- Now: Open question: what baseline would show build times doubled?
- Proposed: no timings from before the cache
- `build-timings.xlsx{PLACE}Evening!A2` · `meeting-notes.md:21`

⊘ `vendor-quote.xlsx` left out: answers none of this proposal's questions
"""


# The revised card from the demo (docs/images/km-still-3-decided.png).
REVISED = {
    "location": "~/notes/cache-policy.md",
    "summary": "Rollout as background, build lead decides",
    "rows": [
        {
            "current": {"text": "Cache sequence as an open question"},
            "proposed": {
                "label": "Background",
                "text": "read cache in 0.4, write cache in 0.5. Not proposed or approved.",
            },
            "sources": [{"file": "meeting-notes.md", "line_number": 15}],
        },
        {
            "current": {
                "label": "Open question",
                "text": "who can settle the conflicting accounts?",
            },
            "proposed": {
                "label": "Approval",
                "text": "build lead decides at Thursday's review",
            },
            "sources": [{"said": "The build lead decides at Thursday's review."}],
        },
    ],
}

REVISED_TABLE = """\
`PROPOSED CHANGES` · `Nothing saved`

**Rollout as background, build lead decides**

| ID | Current | Proposed | Source |
| --- | --- | --- | --- |
| C1 | Cache sequence as an open question | **Background:** read cache in 0.4, write cache in 0.5. Not proposed or approved. | `meeting-notes.md:15` |
| C2 | **Open question:** who can settle the conflicting accounts? | **Approval:** build lead decides at Thursday's review | you, today |
"""


def call(tmp_path, arguments):
    async def steps(client):
        return await client.call_tool("kb_prepare_proposal", arguments)

    return session(server_parameters(tmp_path), steps)


def test_proposal_card_is_a_table_in_the_text_and_the_structured_content(tmp_path):
    result = call(tmp_path, DEMO)

    assert not result.is_error, result.content
    card, data = (block.text for block in result.content)
    assert card == TABLE
    assert json.loads(data) == result.structured_content
    assert result.structured_content["card"] == TABLE
    assert "location" not in result.structured_content


def test_proposal_card_is_a_list_in_a_terminal(tmp_path):
    result = call(tmp_path, {**DEMO, "layout": "list"})

    assert result.structured_content["card"] == LIST
    assert "layout" not in result.structured_content


def test_proposal_text_cannot_break_the_table(tmp_path):
    row = {
        "proposed": {"text": "a | b\nc"},
        "sources": [{"file": "notes `v2`.md", "line_number": 1}],
    }
    result = call(tmp_path, {**DEMO, "rows": [row], "left_out": []})

    card = result.content[0].text
    assert "| C1 | — | a \\| b c | ``notes `v2`.md:1`` |" in card.splitlines()


def test_proposal_source_takes_a_line_or_a_place(tmp_path):
    source = {"file": "build-timings.xlsx", "line_number": 2, "place": "Evening!A2"}
    row = {"proposed": {"text": "x"}, "sources": [source]}
    result = call(tmp_path, {**DEMO, "rows": [row]})

    assert result.is_error
    pointers = [error["pointer"] for error in result.structured_content["errors"]]
    assert pointers
    assert all(found.startswith("#/rows/0/sources/0/") for found in pointers)


def test_revised_card_cites_the_person(tmp_path):
    result = call(tmp_path, REVISED)

    assert result.structured_content["card"] == REVISED_TABLE


def test_a_cited_file_is_not_left_out(tmp_path):
    left_out = [{"file": "meeting-notes.md", "reason": "line 11 conflicts"}]
    result = call(tmp_path, {**DEMO, "left_out": left_out})

    assert result.is_error
    assert result.structured_content["errors"][0]["pointer"] == "#/left_out/0/file"
