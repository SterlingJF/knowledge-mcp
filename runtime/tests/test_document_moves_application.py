from __future__ import annotations

import json
from functools import partial
from hashlib import sha256
from pathlib import Path
from shutil import copytree

import anyio
import pytest
from mcp.client import Client

from knowledge_mcp import document_move, log
from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from knowledge_mcp.models import ListedFile
from knowledge_mcp.models_auto.common_schema import DocumentMove, MoveDocument
from tests.harness import server_parameters, session
from tests.test_document_move_end_to_end import FIXTURE
from tests.test_document_moves_end_to_end import apply, prepare
from tests.test_filing_end_to_end import PERMISSION, typed
from tests.test_template_workflow_end_to_end import disk_snapshot


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


def assert_reviewed_reference_inventory(plan, original):
    note = "Inbox/Note.md"
    moved = "decisions/Reviewed Note.md"
    space = "Inbox/Space Name.md"
    moved_space = "decisions/Space Name.md"
    references = [
        ("References/Index.md", token, note, moved)
        for token in [
            "[[Note]]",
            "[[Note|text]]",
            "[[Note#Heading]]",
            "[[Note#^id]]",
            "![[Note]]",
            "![[Note#Heading]]",
            "![[Note#^id]]",
            "[[Inbox/Note]]",
            "[[Inbox/Note.md]]",
            "[plain](../Inbox/Note.md)",
            "[encoded](../Inbox/Note.md#Heading)",
            '[with title](../Inbox/Note.md "Read the note")',
            '![image](../Inbox/Note.md "Preview")',
            "[note]: ../Inbox/Note.md",
        ]
    ] + [
        (
            "References/Index.md",
            "[encoded space](../Inbox/Space%20Name.md)",
            space,
            moved_space,
        ),
        (
            note,
            "[Diagram](../References/assets/diagram.png)",
            "References/assets/diagram.png",
            "References/assets/diagram.png",
        ),
        (note, "[[Other/Reference]]", "Other/Reference.md", "Other/Reference.md"),
        (note, "[[#Heading]]", note, moved),
        ("Outside/Index.md", "[note](../Inbox/Note.md#Heading)", note, moved),
        ("Outside/Index.md", "[[Inbox/Space Name|space]]", space, moved_space),
        (".hidden/Index.md", "[[Inbox/Note]]", note, moved),
        ("Outside/Ambiguous.md", "[[Index]]", "Same/Index.md", "Same/Index.md"),
    ]
    expected = []
    for source, token, before, after in references:
        text = original[source].decode("utf-8")
        # Whole lines distinguish wiki links from their embedded forms.
        start = (
            next(
                offset
                for offset in range(len(text))
                if (offset == 0 or text[offset - 1] == "\n")
                and text.startswith(token, offset)
            )
            if source == "References/Index.md"
            else text.index(token)
        )
        assert text[start : start + len(token)] == token
        expected.append((source, start, start + len(token), before, after))
    actual = [
        (
            link["source_path"],
            link["start"],
            link["end"],
            link["target_before"],
            link["target_after"],
        )
        for link in plan["links"]
    ]
    assert len(expected) == 22
    assert sorted(actual) == sorted(expected)
    text = original["References/Index.md"].decode("utf-8")
    for example in ("`[[Note]]`", "~~~markdown\n[[Note]]\n~~~"):
        start = text.index(example)
        end = start + len(example)
        assert not any(
            source == "References/Index.md" and start <= a < end
            for source, a, _b, _before, _after in actual
        )


def refuse_stale_reviewed_folder(root, original, writes, parameters):
    async def refuse_stale(client: Client):
        for w in writes:
            path = root / w["old_path"]
            before = path.read_bytes()
            changed = before.replace(b"\n", b"\r\n")
            if changed == before:
                changed += b"\r\n"
            path.write_bytes(changed)
            stale = disk_snapshot(root)
            state = Path(parameters.env["XDG_STATE_HOME"])
            state_before = disk_snapshot(state)
            with pytest.raises(AssertionError, match=w["old_path"]):
                guard_reviewed_writes(root, writes)
            assert disk_snapshot(root) == stale
            assert disk_snapshot(state) == state_before
            assert await reviewed_folder_history(client, root) == []
            path.write_bytes(before)
        assert disk_snapshot(root) == original

    session(parameters, refuse_stale)


def guard_reviewed_writes(root, writes):
    for w in writes:
        assert (
            "sha256:" + sha256((root / w["old_path"]).read_bytes()).hexdigest()
            == w["before_digest"]
        ), w["old_path"]
        if w["path"] != w["old_path"]:
            assert not (root / w["path"]).exists()


@pytest.fixture
def reviewed_folder(tmp_path):
    root = tmp_path / "vault"
    copytree(FIXTURE, root)
    for relative, text in {
        "Inbox/Keep.md": "# Keep\n",
        "Inbox/Untyped.md": "# Unclassified\n",
        "Outside/Index.md": "[note](../Inbox/Note.md#Heading) [[Inbox/Space Name|space]]\n",
        ".hidden/Index.md": "[[Inbox/Note]]\n",
        "Outside/Ambiguous.md": "[[Index]]",
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    original = disk_snapshot(root)
    entries = {
        p: typed(
            audience={"value": "folder reviewer", "status": "confirmed"},
            fingerprint=records.digest(original[p].decode()),
        ).model_copy(update={"set_by": "person"})
        for p in [
            "Inbox/Note.md",
            "Inbox/Space Name.md",
            "Inbox/Keep.md",
            "decisions/cache-policy.md",
            "decisions/queue-policy.md",
        ]
    }
    tracking = root / records.PLACE
    tracking.parent.mkdir(parents=True)
    tracking.write_text(records.dump(entries))
    original = disk_snapshot(root)
    parameters = server_parameters(tmp_path / "state")
    return root, original, entries, parameters


@pytest.mark.parametrize("interrupted", [False, True])
def test_reviewed_folder_physical_group_and_interrupted_reopen(
    tmp_path, reviewed_folder, interrupted
):
    root, original, _entries, parameters = reviewed_folder
    initial = [
        ("Inbox/Note.md", "decisions/Note.md"),
        ("Inbox/Space Name.md", "decisions/Space Name.md"),
        ("Inbox/Keep.md", "decisions/Keep.md"),
    ]
    final = [
        ("Inbox/Note.md", "decisions/Reviewed Note.md"),
        ("Inbox/Space Name.md", "decisions/Space Name.md"),
    ]
    permission = {
        "basis": "accepted_change",
        "text": "Accept only Note to decisions/Reviewed Note.md and Space Name to decisions/Space Name.md, their full-base repairs and classification changes; keep Keep and Untyped in place. Bind Outside/Ambiguous.md [[Index]] to Same/Index.md.",
    }

    plan = session(
        parameters,
        partial(
            preview_reviewed_folder,
            reviewed_folder=reviewed_folder,
            initial=initial,
            final=final,
            permission=permission,
        ),
    )
    assert_reviewed_reference_inventory(plan, original)
    writes = [
        *sorted(
            plan["writes"],
            key=lambda w: (w["old_path"] != "Inbox/Note.md", w["old_path"]),
        ),
        dict(
            old_path=records.PLACE,
            path=records.PLACE,
            text=plan["record"],
            before_digest=records.digest(original[records.PLACE].decode()),
            after_digest=records.digest(plan["record"]),
        ),
    ]
    assert {w["old_path"] for w in writes} == {
        "Inbox/Note.md",
        "Inbox/Space Name.md",
        "References/Index.md",
        "Outside/Index.md",
        ".hidden/Index.md",
        "Outside/Ambiguous.md",
        records.PLACE,
    }
    stage = tmp_path / "staged-originals"
    stage.mkdir()

    refuse_stale_reviewed_folder(root, original, writes, parameters)
    guard_reviewed_writes(root, writes)
    for w in writes:
        retained = stage / w["old_path"]
        retained.parent.mkdir(parents=True, exist_ok=True)
        (root / w["old_path"]).rename(retained)
    progress = tmp_path / "progress.json"
    progress.write_text("[]")

    async def install(client: Client):
        installed = []
        for index, w in enumerate(writes, 1):
            path = root / w["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(w["text"].encode())
            installed.append(
                {
                    "path": w["path"],
                    "digest": "sha256:" + sha256(path.read_bytes()).hexdigest(),
                }
            )
            progress.write_text(json.dumps(installed))
            result = await client.call_tool(
                "kb_record_edit",
                dict(
                    location=str(root),
                    allowed_by=permission,
                    before=(stage / w["old_path"]).read_bytes().decode("utf-8"),
                    after=path.read_bytes().decode("utf-8"),
                    whole_file=True,
                    operation=dict(
                        id="reviewed-folder",
                        index=index,
                        count=len(writes),
                        old_path=w["old_path"],
                        path=w["path"],
                    ),
                ),
            )
            assert not result.is_error
            if interrupted:
                break

    session(parameters, install)

    if interrupted:
        assert_interrupted_folder_recovery(reviewed_folder, writes, stage, progress)
    else:
        assert_completed_folder(reviewed_folder, final, writes, permission)


def assert_interrupted_folder_recovery(reviewed_folder, writes, stage, progress):
    root, original, _entries, parameters = reviewed_folder
    history = partial(reviewed_folder_history, root=root)
    first = writes[0]
    changed = root / first["path"]
    before_later_edit = changed.read_bytes()
    later = before_later_edit.replace(b"\n", b"\r\n")
    assert later != before_later_edit
    assert later.decode("utf-8").replace("\r\n", "\n") == before_later_edit.decode(
        "utf-8"
    )
    changed.write_bytes(later)
    persisted = session(parameters, history)
    assert len(persisted) == 1 and persisted[0]["operation"]["count"] == len(writes)
    assert persisted[0]["operation"]["index"] == 1
    assert persisted[0]["before"].encode() == original[first["old_path"]]
    assert persisted[0]["after_digest"] != records.digest(later.decode())
    ledger = json.loads(progress.read_bytes().decode("utf-8"))
    conflicts = [
        p["path"]
        for p in ledger
        if "sha256:" + sha256((root / p["path"]).read_bytes()).hexdigest()
        != p["digest"]
    ]
    assert conflicts == [first["path"]]
    safe = [w["old_path"] for w in writes[1:]]
    assert all(not (root / p).exists() for p in safe)
    recovery_review = {
        "safe": [
            {"path": p, "digest": records.digest(original[p].decode())} for p in safe
        ],
        "conflicts": conflicts,
    }
    recovery_decision = json.loads(json.dumps(recovery_review))
    for item in recovery_decision["safe"]:
        path = item["path"]
        assert not (root / path).exists()
        assert (
            records.digest((stage / path).read_bytes().decode("utf-8"))
            == item["digest"]
        )
        (stage / path).rename(root / path)
    assert changed.read_bytes() == later
    assert (stage / first["old_path"]).read_bytes() == original[first["old_path"]]
    assert not (root / first["old_path"]).exists()
    assert session(parameters, history) == persisted
    assert disk_snapshot(root) == {
        **{p: t for p, t in original.items() if p != first["old_path"]},
        first["path"]: later,
    }


def assert_completed_folder(reviewed_folder, final, writes, permission):
    root, original, entries, parameters = reviewed_folder
    history = partial(reviewed_folder_history, root=root)
    tracking = root / records.PLACE
    expected = {p: t for p, t in original.items() if p not in {a for a, b in final}}
    expected["decisions/Reviewed Note.md"] = original["Inbox/Note.md"]
    expected["decisions/Space Name.md"] = original["Inbox/Space Name.md"]
    expected["Outside/Index.md"] = (
        b"[note](../decisions/Reviewed%20Note.md#Heading) [[decisions/Space Name|space]]\n"
    )
    expected[".hidden/Index.md"] = b"[[decisions/Reviewed Note]]\n"
    expected["Outside/Ambiguous.md"] = b"[[Same/Index]]"
    expected["References/Index.md"] = b"""[[Reviewed Note]]
[[Reviewed Note|text]]
[[Reviewed Note#Heading]]
[[Reviewed Note#^id]]
![[Reviewed Note]]
![[Reviewed Note#Heading]]
![[Reviewed Note#^id]]
[[decisions/Reviewed Note]]
[[decisions/Reviewed Note.md]]
[plain](../decisions/Reviewed%20Note.md)
[encoded](../decisions/Reviewed%20Note.md#Heading)
[with title](../decisions/Reviewed%20Note.md "Read the note")
![image](../decisions/Reviewed%20Note.md "Preview")
[reference][note]

[note]: ../decisions/Reviewed%20Note.md

[encoded space](../decisions/Space%20Name.md)

`[[Note]]`

~~~markdown
[[Note]]
~~~
"""
    actual = disk_snapshot(root)
    assert {p: t for p, t in actual.items() if p != records.PLACE} == {
        p: t for p, t in expected.items() if p != records.PLACE
    }
    after_entries = records.parse(tracking.read_bytes().decode("utf-8"))
    remap = {
        "Inbox/Note.md": "decisions/Reviewed Note.md",
        "Inbox/Space Name.md": "decisions/Space Name.md",
    }
    assert {p: records.plain(e) for p, e in after_entries.items()} == {
        remap.get(p, p): records.plain(e) for p, e in entries.items()
    }
    persisted = session(parameters, history)
    assert len(persisted) == len(writes)
    for index, (e, w) in enumerate(zip(persisted, writes, strict=True), 1):
        assert e["operation"] == dict(
            id="reviewed-folder",
            index=index,
            count=len(writes),
            old_path=w["old_path"],
            path=w["path"],
        )
        assert e["allowed_by"] == permission
        assert e["before"].encode() == original[w["old_path"]]
        assert e["after_digest"] == records.digest(actual[w["path"]].decode())


def test_batch_accepts_exact_row_and_utf8_input_limits():
    # Exercise the native inventory/input boundary without materializing a giant answer.
    text = "é" * (document_move.MAX_BYTES // 2)
    request = document_move.BatchRequest(
        location="vault",
        moves=[DocumentMove(old_path=f"{i}.md", path=f"D/{i}.md") for i in range(1000)],
        listing=[ListedFile(path=f"{i}.md") for i in range(1000)],
        documents=[
            MoveDocument(path=f"{i}.md", text=text if i == 0 else "")
            for i in range(1000)
        ],
        case_mode="sensitive",
        bindings=[],
        searched=False,
        search=[],
        allowed_by=None,
        knowledge_bus_folders=[],
    )
    paths, documents = document_move._batch_inputs(request)
    assert len(paths) == len(documents) == 1000
    assert len(documents["0.md"].encode()) == 33554432
    request.documents[0].text += "a"
    assert sum(len(d.text.encode("utf-8")) for d in request.documents) == 33554433
    with pytest.raises(
        document_move.MoveError, match="measured 33554433 UTF-8 text bytes"
    ):
        document_move._batch_inputs(request)


def test_batch_accepts_exact_serialized_answer_limit():
    prefix_bytes = len(
        json.dumps({"text": ""}, ensure_ascii=False, separators=(",", ":")).encode()
    )
    result = {"text": "a" * (33554432 - prefix_bytes)}
    assert (
        len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
        == 33554432
    )
    document_move.check_batch_size(result)
    result["text"] += "a"
    assert (
        len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode())
        == 33554433
    )
    with pytest.raises(document_move.MoveError, match="measured 33554433"):
        document_move.check_batch_size(result)


async def preview_reviewed_folder(
    client: Client, reviewed_folder, initial, final, permission
):
    root, original, _entries, _parameters = reviewed_folder
    tracking = root / records.PLACE
    args = dict(
        location=str(root),
        knowledge_bus_folders=[],
        record=tracking.read_bytes().decode("utf-8"),
        listing=[{"path": p} for p in original],
        documents=[
            {"path": p, "text": t.decode()}
            for p, t in original.items()
            if p.endswith(".md")
        ],
        case_mode="sensitive",
    )

    async def prepare_rows(rows, **extra):
        request = dict(
            **args, moves=[dict(old_path=a, path=b) for a, b in rows], **extra
        )
        first = await client.call_tool("kb_prepare_document_moves", request)
        assert (
            not first.is_error and first.structured_content["status"] == "texts_needed"
        )
        assert first.structured_content["writes"] == []
        incomplete = await client.call_tool(
            "kb_prepare_document_moves", dict(**request, searched=True, search=[])
        )
        assert (
            not incomplete.is_error
            and incomplete.structured_content["status"] == "texts_needed"
        )
        assert incomplete.structured_content["writes"] == []
        result = await client.call_tool(
            "kb_prepare_document_moves",
            dict(**request, searched=True, search=first.structured_content["search"]),
        )
        assert not result.is_error
        return result.structured_content

    blocked = await prepare_rows(initial)
    assert blocked["status"] == "blocked" and blocked["writes"] == []
    assert any(i["code"] == "link-ambiguous" for i in blocked["issues"])
    binding = [
        dict(
            source_path="Outside/Ambiguous.md",
            start=0,
            end=9,
            target_path="Same/Index.md",
        )
    ]
    proposed = await prepare_rows(initial, bindings=binding)
    assert proposed["status"] == "permission_needed" and proposed["writes"] == []
    assert len(proposed["moves"]) == 3
    revised = await prepare_rows(final, bindings=binding)
    assert revised["status"] == "permission_needed" and revised["record"] is None
    approved = await prepare_rows(final, bindings=binding, allowed_by=permission)
    assert approved["status"] == "ready", approved["issues"]
    assert approved["moves"] == [dict(old_path=a, path=b) for a, b in final]
    assert disk_snapshot(root) == original
    return approved


async def reviewed_folder_history(client: Client, root):
    tracking = root / records.PLACE
    if tracking.exists() and "decisions/Reviewed Note.md" in records.parse(
        tracking.read_bytes().decode("utf-8")
    ):
        result = await client.call_tool(
            "kb_get_document_type",
            dict(
                location=str(root),
                name="Reviewed Note.md",
                folders=["decisions"],
                knowledge_bus_folders=[],
                record=tracking.read_bytes().decode("utf-8"),
                listing=[{"path": p} for p in disk_snapshot(root)],
            ),
        )
        assert not result.is_error
        assert result.structured_content["recorded"]["entry"] == records.plain(
            records.parse(tracking.read_bytes().decode("utf-8"))[
                "decisions/Reviewed Note.md"
            ]
        )
    result = await client.call_tool("kb_list_edits", {"location": str(root)})
    assert not result.is_error
    return result.structured_content["edits"]
