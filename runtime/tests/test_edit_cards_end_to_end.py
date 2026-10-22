from __future__ import annotations

from tests.harness import server_parameters, session

ACCEPTED = {
    "basis": "accepted_change",
    "text": "Save it.",
}

CARD = """\
`Saved` · **Approved revision saved**

The edit to `cache-policy.md` is recorded.
"""


def record(tmp_path, allowed_by):
    async def steps(client):
        return await client.call_tool(
            "kb_record_edit",
            {
                "location": "~/notes/cache-policy.md",
                "allowed_by": allowed_by,
                "before": "## Open question\n",
                "after": "## Approval\n\nThe build lead decides at Thursday's review.\n",
            },
        )

    return session(server_parameters(tmp_path), steps)


def test_saved_card_is_in_the_text_and_the_structured_content(tmp_path):
    result = record(tmp_path, ACCEPTED)

    assert not result.is_error, result.content
    assert result.content[0].text == CARD
    assert result.structured_content["card"] == CARD


def test_saved_card_for_a_request_says_edit(tmp_path):
    request = {"basis": "request", "text": "Add an approval section."}
    result = record(tmp_path, request)

    assert result.structured_content["card"].startswith("`Saved` · **Edit saved**")


def test_pickup_card_names_the_latest_edit(tmp_path):
    async def steps(client):
        await client.call_tool(
            "kb_record_edit",
            {
                "location": "~/notes/cache-policy.md",
                "allowed_by": ACCEPTED,
                "before": "## Open question\n",
                "after": "## Approval\n",
            },
        )
        return await client.call_tool(
            "kb_list_edits", {"location": "~/notes/cache-policy.md"}
        )

    result = session(server_parameters(tmp_path), steps)

    assert result.structured_content["card"] == (
        "`APPROVED REVISION` · `cache-policy.md`\n"
    )


def test_pickup_has_no_card_when_nothing_is_recorded(tmp_path):
    async def steps(client):
        return await client.call_tool("kb_list_edits", {"location": "~/notes/new.md"})

    result = session(server_parameters(tmp_path), steps)

    assert "card" not in result.structured_content
    assert len(result.content) == 1
