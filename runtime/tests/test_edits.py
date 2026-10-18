from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.harness import server_parameters, session, texts, write

FIXTURE_DIR = Path(__file__).parent / "fixtures"

DESIGN = "DESIGN.md"
BEFORE = (
    (FIXTURE_DIR / "design-before-overview-insertion.md").read_bytes().decode("utf-8")
)
AFTER = (
    (FIXTURE_DIR / "design-after-overview-insertion.md").read_bytes().decode("utf-8")
)


def digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def ask(state: Path, *calls: tuple[str, dict]) -> list:
    async def steps(client):
        return [await client.call_tool(name, arguments) for name, arguments in calls]

    return session(server_parameters(state), steps)


def answer(result) -> dict:
    assert not result.is_error, texts(result)
    [text] = texts(result)
    return json.loads(text)


def logged(state: Path) -> list[dict]:
    log = state / "knowledge-mcp" / "log.jsonl"
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_edit_listing_returns_text_for_manual_undo(tmp_path):
    root = tmp_path / "site"
    path = write(root, DESIGN, BEFORE)
    location = str(path)
    request = "Add an Overview section to DESIGN.md."
    path.write_text(AFTER)
    recorded, listed = ask(
        tmp_path / "state",
        (
            "kb_record_edit",
            {
                "location": location,
                "allowed_by": {
                    "basis": "request",
                    "text": request,
                },
                "before": BEFORE,
                "after": AFTER,
            },
        ),
        ("kb_list_edits", {"location": location}),
    )

    receipt = answer(recorded)
    assert receipt["schema"] == "knowledge-mcp/edit/1"
    assert receipt["before_digest"] == digest(BEFORE)
    assert receipt["after_digest"] == digest(AFTER)
    assert "before" not in receipt and "after" not in receipt

    edits = answer(listed)
    assert edits["schema"] == "knowledge-mcp/edits/1"
    [edit] = edits["edits"]
    assert edit["id"] == receipt["id"]
    assert edit["allowed_by"] == {"basis": "request", "text": request}
    assert edit["location"] == location
    assert digest(path.read_text()) == edit["after_digest"]
    path.write_text(path.read_text().replace(edit["after"], edit["before"]))
    assert path.read_text() == BEFORE

    entries = logged(tmp_path / "state")
    assert [entry["tool"] for entry in entries] == ["kb_record_edit", "kb_list_edits"]
    assert [entry["returned"] for entry in entries] == [
        texts(recorded),
        texts(listed),
    ]


def test_edit_records_preserve_instruction_and_accepted_change_authorization(tmp_path):
    location = "https://www.notion.so/team/Design-0123456789abcdef"
    line = "Agents may fill in empty sections of design notes."
    row = "Overview: add the personality line. Evidence: brand review."
    recorded = ask(
        tmp_path / "state",
        (
            "kb_record_edit",
            {
                "location": location,
                "allowed_by": {
                    "basis": "instruction",
                    "text": line,
                    "location": "AGENTS.md",
                },
                "before": "",
                "after": "## Overview\n",
            },
        ),
        (
            "kb_record_edit",
            {
                "location": location,
                "allowed_by": {
                    "basis": "accepted_change",
                    "text": row,
                },
                "before": "## Overview\n",
                "after_digest": digest("## Overview\n\nCalm.\n"),
                "whole_file": True,
            },
        ),
        ("kb_list_edits", {"location": location}),
    )

    first, second = (edit for edit in answer(recorded[-1])["edits"])
    assert first["allowed_by"] == {
        "basis": "instruction",
        "text": line,
        "location": "AGENTS.md",
    }
    assert first["before"] == ""
    assert second["allowed_by"] == {"basis": "accepted_change", "text": row}
    assert "after" not in second
    assert second["after_digest"] == digest("## Overview\n\nCalm.\n")
    assert second["whole_file"] is True
    assert "whole_file" not in first


def test_edit_records_persist_across_sessions_per_location(tmp_path):
    state = tmp_path / "state"

    def record(location: str, after: str) -> tuple[str, dict]:
        return (
            "kb_record_edit",
            {
                "location": location,
                "allowed_by": {
                    "basis": "request",
                    "text": "Fix the typo.",
                },
                "before": BEFORE,
                "after": after,
            },
        )

    ask(state, record("/kb/a.md", AFTER), record("/kb/b.md", AFTER))
    ask(state, record("/kb/a.md", AFTER + "More.\n"))
    [a, b, c] = ask(
        state,
        ("kb_list_edits", {"location": "/kb/a.md"}),
        ("kb_list_edits", {"location": "/kb/b.md"}),
        ("kb_list_edits", {"location": "/kb/c.md"}),
    )

    assert [edit["after"] for edit in answer(a)["edits"]] == [AFTER, AFTER + "More.\n"]
    assert len(answer(b)["edits"]) == 1
    assert answer(c)["edits"] == []


def test_edit_record_uses_private_state_file(tmp_path):
    root = tmp_path / "site"
    path = write(root, DESIGN, AFTER)
    before = sorted(p.relative_to(root) for p in root.rglob("*"))

    ask(
        tmp_path / "state",
        (
            "kb_record_edit",
            {
                "location": str(path),
                "allowed_by": {
                    "basis": "request",
                    "text": "Add an Overview.",
                },
                "before": BEFORE,
                "after": AFTER,
            },
        ),
    )

    record = tmp_path / "state" / "knowledge-mcp" / "edits.jsonl"
    assert oct(record.stat().st_mode & 0o777) == "0o600"
    [line] = record.read_text().splitlines()
    assert json.loads(line)["before"] == BEFORE
    assert sorted(p.relative_to(root) for p in root.rglob("*")) == before


def test_invalid_after_data_creates_no_records(tmp_path):
    base = {
        "location": "/kb/a.md",
        "allowed_by": {
            "basis": "request",
            "text": "Fix the typo.",
        },
        "before": BEFORE,
    }
    passage, malformed, upper = ask(
        tmp_path / "state",
        ("kb_record_edit", {**base, "after_digest": digest(AFTER)}),
        (
            "kb_record_edit",
            {**base, "after_digest": "sha256:abc", "whole_file": True},
        ),
        (
            "kb_record_edit",
            {**base, "after_digest": digest(AFTER).upper(), "whole_file": True},
        ),
    )
    missing, mismatched, listed = ask(
        tmp_path / "state",
        ("kb_record_edit", base),
        ("kb_record_edit", {**base, "after": AFTER, "after_digest": digest(BEFORE)}),
        ("kb_list_edits", {"location": "/kb/a.md"}),
    )

    assert missing.is_error and "`after`" in texts(missing)[0]
    assert mismatched.is_error and "`after_digest`" in texts(mismatched)[0]
    # Undo needs the replacement text to locate the edited passage.
    assert passage.is_error and "`whole_file`" in texts(passage)[0]
    assert malformed.is_error and "64 lowercase hex" in texts(malformed)[0]
    assert upper.is_error and "64 lowercase hex" in texts(upper)[0]
    assert answer(listed)["edits"] == []


def test_an_unknown_basis_is_refused(tmp_path):
    arguments = {
        "location": "/kb/a.md",
        "allowed_by": {
            "basis": "the agent thought it best",
            "text": "",
        },
        "before": BEFORE,
        "after": AFTER,
    }
    [result] = ask(tmp_path / "state", ("kb_record_edit", arguments))

    assert result.is_error
    assert "basis" in texts(result)[0]
    [entry] = logged(tmp_path / "state")
    assert entry["tool"] == "kb_record_edit"
    assert entry["location"] == "/kb/a.md"
    assert entry["returned"] == texts(result)
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    assert entry["sent"] == digest(canonical)
