from __future__ import annotations

from tests.harness import server_parameters, session

ACCEPTED = {
    "basis": "accepted_change",
    "text": "Save it.",
}

CARD = """\
`Saved` · **Approved revision saved**

The edit to `cache-policy.md` is recorded.

`cache-policy.md` · 1 change

- ~~## Open question~~
- ## Approval
- (blank line added)
- The build lead decides at Thursday's review.
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


def call(tmp_path, *arguments):
    async def steps(client):
        results = []
        for sent in arguments:
            results.append(await client.call_tool("kb_record_edit", sent))
        return results

    return session(server_parameters(tmp_path), steps)


def edit(**fields):
    return {"location": "~/notes/cache-proposal.md", "allowed_by": ACCEPTED, **fields}


def test_changes_list_removed_and_added_lines_in_document_order(tmp_path):
    before = "Title: Build schedule and cache rollout\nkeep\nold\n"
    after = "Title: Evening build retirement\nkeep\nnew\n"
    (result,) = call(tmp_path, edit(before=before, after=after))

    assert result.structured_content["changes"] == {
        "hunks": 2,
        "lines": [
            {"change": "removed", "text": "Title: Build schedule and cache rollout"},
            {"change": "added", "text": "Title: Evening build retirement"},
            {"change": "removed", "text": "old"},
            {"change": "added", "text": "new"},
        ],
        "more": 0,
    }
    card = result.structured_content["card"]
    assert "`cache-proposal.md` · 2 changes" in card
    assert (
        "- ~~Title: Build schedule and cache rollout~~\n- Title: Evening build retirement"
        in card
    )
    assert "created" not in result.structured_content


def test_changes_are_capped_with_a_count_of_lines_left_out(tmp_path):
    after = "".join(f"line {n}\n" for n in range(20))
    (result,) = call(tmp_path, edit(before="", after=after, whole_file=True))

    found = result.structured_content["changes"]
    assert found["hunks"] == 1
    assert len(found["lines"]) == 12
    assert found["more"] == 8
    assert "- … and 8 more changed lines" in result.structured_content["card"]


def test_created_is_set_when_before_is_empty(tmp_path):
    (result,) = call(tmp_path, edit(before="", after="# New\n", whole_file=True))

    assert result.structured_content["created"] is True
    assert (
        "The creation of `cache-proposal.md` is recorded."
        in result.structured_content["card"]
    )


def test_digest_only_edit_has_no_changes(tmp_path):
    digest = "sha256:" + "0" * 64
    (result,) = call(tmp_path, edit(before="x\n", after_digest=digest, whole_file=True))

    assert not result.is_error, result.content
    assert "changes" not in result.structured_content


def test_undoes_is_echoed_when_the_earlier_edit_exists(tmp_path):
    async def steps(client):
        first = await client.call_tool(
            "kb_record_edit", edit(before="a\n", after="b\n")
        )
        earlier = first.structured_content["id"]
        return earlier, await client.call_tool(
            "kb_record_edit", edit(before="b\n", after="a\n", undoes=earlier)
        )

    earlier, result = session(server_parameters(tmp_path), steps)

    assert result.structured_content["undoes"] == earlier
    assert f"It undoes edit `{earlier}`." in result.structured_content["card"]


def test_undoes_an_unknown_edit_is_refused(tmp_path):
    (result,) = call(tmp_path, edit(before="b\n", after="a\n", undoes="f" * 32))

    assert result.is_error
    assert result.structured_content["errors"][0]["pointer"] == "#/undoes"


def test_empty_before_without_whole_file_is_not_a_creation(tmp_path):
    (result,) = call(tmp_path, edit(before="", after="An inserted line\n"))

    assert "created" not in result.structured_content


def test_undoes_an_edit_of_another_document_is_refused(tmp_path):
    async def steps(client):
        other = {**edit(before="a\n", after="b\n"), "location": "~/notes/other.md"}
        first = await client.call_tool("kb_record_edit", other)
        return await client.call_tool(
            "kb_record_edit",
            edit(before="b\n", after="a\n", undoes=first.structured_content["id"]),
        )

    result = session(server_parameters(tmp_path), steps)

    assert result.is_error
    assert result.structured_content["errors"][0]["pointer"] == "#/undoes"
