from __future__ import annotations

import anyio
import pytest

from knowledge_mcp import document_types as records
from knowledge_mcp import log
from knowledge_mcp.main import build_server
from tests.test_document_moves_end_to_end import apply, prepare
from tests.test_filing_end_to_end import PERMISSION


@pytest.mark.parametrize(
    "moves",
    [
        [("A.md", "X.md"), ("B.md", "Y.md")],
        [("A.md", "B.md"), ("B.md", "A.md")],
        [("A.md", "B.md"), ("B.md", "C.md")],
    ],
)
def test_whole_list_undo_and_later_change_guard(moves):
    docs = {"A.md": "[[B#Heading]]", "B.md": "[[A#^block]]", "Index.md": "[[A]] [[B]]"}
    forward = prepare(docs, moves)
    after = apply(docs, forward)
    undo = prepare(after, [(b, a) for a, b in moves])
    assert apply(after, undo) == docs
    changed = dict(after)
    changed[moves[0][1]] += "\nLater edit."
    with pytest.raises(AssertionError):
        apply(changed, undo)
    assert "Later edit." in changed[moves[0][1]]


def fail_write():
    raise OSError


@pytest.mark.parametrize("fail_at", range(8))
def test_staged_application_failure_preserves_originals(fail_at):
    docs = {"A.md": "[[B]]", "B.md": "[[A]]", "Index.md": "[[A]] [[B]]"}
    plan = prepare(docs, [("A.md", "B.md"), ("B.md", "A.md")])
    current = dict(docs)
    retained = dict(docs)
    staged = {}
    installed = {}
    step = 0
    try:
        for w in plan["writes"]:
            if step == fail_at:
                fail_write()
            staged[w["old_path"]] = current.pop(w["old_path"])
            step += 1
        for w in plan["writes"]:
            if step == fail_at:
                fail_write()
            current[w["path"]] = w["text"]
            installed[w["path"]] = w["after_digest"]
            step += 1
        for _ in range(2):
            if step == fail_at:
                fail_write()
            step += 1
    except OSError:
        for p, digest in installed.items():
            assert records.digest(current[p]) == digest
        for p in installed:
            current.pop(p)
        current.update(staged)
        assert current == retained


def grouped_records(server, docs, plan):
    count = len(plan["writes"]) + 1
    for index, w in enumerate(plan["writes"], 1):
        result = anyio.run(
            server.call_tool,
            "kb_record_edit",
            dict(
                location="vault",
                allowed_by=PERMISSION,
                before=docs[w["old_path"]],
                after=w["text"],
                whole_file=True,
                operation=dict(
                    id="whole-list",
                    index=index,
                    count=count,
                    old_path=w["old_path"],
                    path=w["path"],
                ),
            ),
        )
        assert not result.is_error
    result = anyio.run(
        server.call_tool,
        "kb_record_edit",
        dict(
            location="vault",
            allowed_by=PERMISSION,
            before="",
            after=plan["record"],
            whole_file=True,
            operation=dict(
                id="whole-list",
                index=count,
                count=count,
                old_path=records.PLACE,
                path=records.PLACE,
            ),
        ),
    )
    assert not result.is_error
    return anyio.run(
        server.call_tool, "kb_list_edits", dict(location="vault")
    ).structured_content["edits"]


def undo_conflicts(entries, current):
    count = entries[0]["operation"]["count"]
    if len(entries) != count or {e["operation"]["index"] for e in entries} != set(
        range(1, count + 1)
    ):
        return ["incomplete group"]
    return [
        e["operation"]["path"]
        for e in entries
        if records.digest(current.get(e["operation"]["path"], "")) != e["after_digest"]
    ]


@pytest.mark.parametrize(
    "moves",
    [
        [("A.md", "X.md"), ("B.md", "Y.md")],
        [("A.md", "B.md"), ("B.md", "A.md")],
        [("A.md", "B.md"), ("B.md", "C.md")],
    ],
)
def test_grouped_undo_guards_configuration_and_incomplete_group(
    tmp_path, monkeypatch, moves
):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    server = build_server()
    original = {"A.md": "[[B]]", "B.md": "[[A]]", "Ref.md": "[[A]] [[B]]"}
    plan = prepare(original, moves)
    current = apply(original, plan)
    current[records.PLACE] = plan["record"]
    entries = grouped_records(server, original, plan)
    assert undo_conflicts(entries, current) == []
    assert undo_conflicts(entries[:-1], current) == ["incomplete group"]
    for entry in entries:
        changed = dict(current)
        path = entry["operation"]["path"]
        changed[path] += "\nLater edit."
        assert undo_conflicts(entries, changed) == [path]
        assert changed[path].endswith("Later edit.")
    inverse = prepare(
        {p: t for p, t in current.items() if p != records.PLACE},
        [(b, a) for a, b in moves],
    )
    restored = apply({p: t for p, t in current.items() if p != records.PLACE}, inverse)
    for entry in entries:
        restored[entry["operation"]["old_path"]] = entry["before"]
    assert {p: t for p, t in restored.items() if p != records.PLACE} == original


def test_filesystem_swap_staging_and_recovery_preserves_concurrent_bytes(tmp_path):
    original = {"A.md": "[[B]]", "B.md": "[[A]]"}
    plan = prepare(original, [("A.md", "B.md"), ("B.md", "A.md")])
    stage = tmp_path / "recovery"
    stage.mkdir()
    for p, t in original.items():
        (tmp_path / p).write_text(t)
    for w in plan["writes"]:
        (tmp_path / w["old_path"]).rename(stage / w["old_path"])
    for w in plan["writes"]:
        assert not (tmp_path / w["path"]).exists()
        (tmp_path / w["path"]).write_text(w["text"])
    (tmp_path / "B.md").write_text("Concurrent text.")
    conflicts = []
    for w in plan["writes"]:
        path = tmp_path / w["path"]
        if records.digest(path.read_text()) != w["after_digest"]:
            conflicts.append(w["path"])
        else:
            path.rename(stage / ("installed-" + w["path"]))
    for w in plan["writes"]:
        path = tmp_path / w["old_path"]
        if path.exists():
            conflicts.append(w["old_path"])
        else:
            (stage / w["old_path"]).rename(path)
    assert set(conflicts) == {"B.md"}
    assert (tmp_path / "B.md").read_text() == "Concurrent text."
    assert (stage / "B.md").exists()


def test_recording_retry_keeps_installed_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    docs = {"A.md": "same text"}
    plan = prepare(docs, [("A.md", "B.md")])
    installed = apply(docs, plan)
    server = build_server()
    original_append = log.append

    def failed_append(name, entry):
        if name == "edits.jsonl":
            message = "simulated record failure"
            raise OSError(message)
        original_append(name, entry)

    monkeypatch.setattr(log, "append", failed_append)
    with pytest.raises(AssertionError):
        grouped_records(server, docs, plan)
    assert installed == {"B.md": "same text"}
    monkeypatch.setattr(log, "append", original_append)
    entries = grouped_records(server, docs, plan)
    assert (
        len(entries) == 2 and entries[0]["before_digest"] == entries[0]["after_digest"]
    )
    assert installed == {"B.md": "same text"}


def test_answer_log_failure_keeps_record_for_retry(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    server = build_server()
    args = dict(
        location="vault",
        allowed_by=PERMISSION,
        before="same",
        after="same",
        whole_file=True,
        operation=dict(id="operation", index=1, count=1, old_path="A.md", path="B.md"),
    )
    original = log.append

    def fail_answer_log(name, entry):
        if name == "log.jsonl":
            message = "simulated answer log failure"
            raise OSError(message)
        original(name, entry)

    monkeypatch.setattr(log, "append", fail_answer_log)
    result = anyio.run(server.call_tool, "kb_record_edit", args)
    assert result.is_error
    monkeypatch.setattr(log, "append", original)
    listed = anyio.run(server.call_tool, "kb_list_edits", dict(location="vault"))
    assert not listed.is_error
    entries = listed.structured_content["edits"]
    assert len(entries) == 1 and entries[0]["operation"] == args["operation"]


def test_forward_digest_guard_keeps_newer_source():
    original = {"A.md": "[[B]]", "B.md": "[[A]]"}
    plan = prepare(original, [("A.md", "B.md"), ("B.md", "A.md")])
    changed = {**original, "A.md": "Later source bytes."}
    with pytest.raises(AssertionError):
        apply(changed, plan)
    assert changed["A.md"] == "Later source bytes."
