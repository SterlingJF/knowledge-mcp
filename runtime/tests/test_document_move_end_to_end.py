from __future__ import annotations

from pathlib import Path
from shutil import copytree
from typing import Any
from urllib.parse import quote

import anyio
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from knowledge_mcp import document_types as records
from knowledge_mcp.main import build_server
from tests.harness import BUNDLED, CODEBASE, PRODUCT, header, server_parameters, session
from tests.test_filing_end_to_end import PERMISSION, call, typed

FIXTURE = Path(__file__).parent / "fixtures/b1-vault"


def vault():
    return {
        p.relative_to(FIXTURE).as_posix(): p.read_text()
        for p in FIXTURE.rglob("*")
        if p.is_file()
    }


def arguments(docs, old="Inbox/Note.md", path="decisions/Note.md", **extra):
    return dict(
        location="unreachable://vault",
        old_path=old,
        path=path,
        listing=[{"path": p} for p in docs],
        documents=[{"path": old, "text": docs[old]}],
        case_mode="sensitive",
        record=records.dump({old: typed()}),
        knowledge_bus_folders=extra.pop("knowledge_bus_folders", []),
        allowed_by=PERMISSION,
        **extra,
    )


def invoke(server, args):
    result = anyio.run(server.call_tool, "kb_prepare_document_move", args)
    assert not result.is_error, result.structured_content
    return result.structured_content


def prepare(docs, **extra):
    server = build_server()
    args = arguments(docs, **extra)
    first = invoke(server, args)
    assert first["status"] == "texts_needed"
    assert first["writes"] == []
    args.update(
        documents=[
            {"path": p, "text": t} for p, t in docs.items() if p.lower().endswith(".md")
        ],
        searched=True,
        search=first["search"],
    )
    return invoke(server, args)


def apply(docs, plan):
    assert plan["status"] == "ready", plan["issues"]
    after = dict(docs)
    for w in plan["writes"]:
        assert records.digest(after[w["old_path"]]) == w["before_digest"]
    for w in plan["writes"]:
        after.pop(w["old_path"])
        after[w["path"]] = w["text"]
        assert records.digest(w["text"]) == w["after_digest"]
    return after


def test_l01_l08_l10_l11_l12_move_and_rename():
    docs = vault()
    for old, new in [
        ("Inbox/Note.md", "decisions/Note.md"),
        ("decisions/Note.md", "decisions/Cache Plan.md"),
    ]:
        before = docs
        plan = prepare(docs, old=old, path=new)
        docs = apply(docs, plan)
        # These targets come from the published syntax and fixture paths, independently of the resolver.
        assert [
            link["target_before"]
            for link in plan["links"]
            if link["source_path"] == old
        ] == ["References/assets/diagram.png", "Other/Reference.md", old]
        assert [
            link["target_before"]
            for link in plan["links"]
            if link["source_path"] == "References/Index.md"
        ] == [old] * 14 + ["Inbox/Space Name.md"]
        for link in plan["links"]:
            expected = new if link["target_before"] == old else link["target_before"]
            assert link["target_after"] == expected
        text = docs["References/Index.md"]
        assert f"[plain](../{new.replace(' ', '%20')})" in text
        assert "#Heading" in text and "#^id" in text and "|text" in text
        assert '"Read the note"' in text
        assert "`[[Note]]`\n\n~~~markdown\n[[Note]]\n~~~" in text
        assert "[Diagram](../References/assets/diagram.png)" in docs[new]
        assert docs["Other/Reference.md"] == before["Other/Reference.md"]


def test_r2_search_echo():
    docs = vault()
    server = build_server()
    args = arguments(docs)
    first = invoke(server, args)
    assert {"Note", "Inbox/Note", "Inbox/Note.md", "Original note"} <= set(
        first["search"]
    )
    for searched, search in [
        (False, first["search"]),
        (True, ["wrong"]),
        (True, first["search"] + ["extra"]),
    ]:
        a = invoke(server, {**args, "searched": searched, "search": search})
        assert a["status"] == "texts_needed" and not a["writes"]


def test_l02_duplicate_introduced():
    docs = vault()
    docs["Other/Reference.md"] = "[[References/Index]] [[Same/Index]]"
    after = apply(docs, prepare(docs, path="decisions/Index.md"))
    assert after["Other/Reference.md"] == docs["Other/Reference.md"]
    assert "[[decisions/Index]]" in after["References/Index.md"]


def test_l03_occupied():
    a = prepare(vault(), path="Other/Reference.md")
    assert a["status"] == "blocked" and not a["writes"] and a["record"] is None


def test_l04_l05_ambiguity_and_binding():
    docs = vault()
    docs["Other/Reference.md"] = "[[Index]]"
    a = prepare(docs)
    assert a["status"] == "blocked"
    issue = next(i for i in a["issues"] if i["code"] == "link-ambiguous")
    assert (issue["source_path"], issue["start"], issue["end"]) == (
        "Other/Reference.md",
        0,
        9,
    )
    a = prepare(
        docs,
        bindings=[
            dict(
                source_path="Other/Reference.md",
                start=0,
                end=9,
                target_path="Same/Index.md",
            )
        ],
    )
    assert "[[Same/Index]]" in apply(docs, a)["Other/Reference.md"]


@pytest.mark.parametrize("mode", ["sensitive", "insensitive"])
def test_l06_case_ambiguity(mode):
    docs = vault()
    docs["Other/Reference.md"] = "[[note]]"
    args = arguments(docs)
    args["case_mode"] = mode
    server = build_server()
    first = invoke(server, args)
    args.update(
        searched=True,
        search=first["search"],
        documents=[
            {"path": p, "text": t} for p, t in docs.items() if p.endswith(".md")
        ],
    )
    assert invoke(server, args)["status"] == "blocked"


@pytest.mark.parametrize("mode", ["sensitive", "insensitive"])
def test_l07_case_only(mode):
    docs = vault()
    server = build_server()
    args = arguments(docs)
    args.update(path="Inbox/note.md", case_mode=mode)
    first = invoke(server, args)
    args.update(
        searched=True,
        search=first["search"],
        documents=[dict(path=p, text=t) for p, t in docs.items() if p.endswith(".md")],
    )
    apply(docs, invoke(server, args))


@pytest.mark.parametrize("name", ["Space Name", "Café", "100%", "Hash#Name"])
def test_l09_encoding(name):
    docs = vault()
    docs["References/Index.md"] += (
        f"\n[encoded](../Inbox/{quote(name, safe='')}.md#Heading)\n"
    )
    docs[f"Inbox/{name}.md"] = "# Encoding\n"
    a = prepare(docs, old=f"Inbox/{name}.md", path=f"decisions/{name}.md")
    assert (
        f"../decisions/{quote(name, safe='')}.md#Heading"
        in apply(docs, a)["References/Index.md"]
    )


def test_l13_coverage():
    args = arguments(vault())
    args["documents"] = []
    result = anyio.run(build_server().call_tool, "kb_prepare_document_move", args)
    assert result.is_error


def test_l14_unsupported():
    docs = vault()
    docs["Other/Reference.md"] = '<a href="../Inbox/Note.md">note</a>'
    a = prepare(docs)
    assert a["status"] == "blocked"


def test_l15_concurrent_digest():
    docs = vault()
    a = prepare(docs)
    docs["References/Index.md"] += "\nNew concurrent text.\n"
    with pytest.raises(AssertionError):
        apply(docs, a)
    after = apply(docs, prepare(docs))
    assert "New concurrent text." in after["References/Index.md"]


def fail_write():
    message = "simulated write failure"
    raise OSError(message)


def test_l16_recovery():
    docs = vault()
    original = dict(docs)
    plan = prepare(docs)
    written = []
    try:
        for w in plan["writes"]:
            if written:
                fail_write()
            docs = apply(docs, {**plan, "writes": [w]})
            written.append(w)
    except OSError:
        for w in reversed(written):
            assert records.digest(docs[w["path"]]) == w["after_digest"]
            docs.pop(w["path"])
            docs[w["old_path"]] = original[w["old_path"]]
    assert docs == original


def test_l17_l18_no_filesystem_and_broken():
    docs = vault()
    docs["Other/Reference.md"] += (
        "\n[[Missing]]\n[external](https://example.com/Note)\n"
    )
    a = prepare(docs)
    assert a["status"] == "ready"
    assert any(i["code"] == "link-broken" for i in a["issues"])
    assert apply(docs, a)["Other/Reference.md"] == docs["Other/Reference.md"]


@pytest.mark.parametrize(
    ("setter", "reader"),
    [
        ("agent", None),
        ("agent", {"value": "product lead", "status": "guessed"}),
        ("person", {"value": "product lead", "status": "confirmed"}),
    ],
)
def test_d01_d02_preserve_entry(setter, reader):
    docs = vault()
    args = arguments(docs)
    entry = typed(**({"audience": reader} if reader else {})).model_copy(
        update={"set_by": setter}
    )
    args["record"] = records.dump({args["old_path"]: entry})
    server = build_server()
    first = invoke(server, args)
    args.update(
        searched=True,
        search=first["search"],
        documents=[
            {"path": p, "text": t} for p, t in docs.items() if p.endswith(".md")
        ],
    )
    a = invoke(server, args)
    kept = records.plain(records.parse(a["record"])[args["path"]])
    before = records.plain(entry)
    kept.pop("fingerprint", None)
    before.pop("fingerprint", None)
    assert kept == before


def test_d03_destination_type_absent():
    docs = vault()
    text = (BUNDLED / PRODUCT / "universe.kbp.yaml").read_text()
    # Keep the universe spec id while removing the saved document type.
    text = text.replace("decision-record", "other-record")
    folder = {
        "folder": "decisions",
        "files": [{"name": "changed.kbp.yaml", **header(text), "text": text}],
    }
    a = prepare(docs, knowledge_bus_folders=[folder])
    assert a["status"] == "blocked"
    assert any(i["code"] == "destination-type-conflict" for i in a["issues"])


@pytest.mark.parametrize(
    "reference", ["[[./Note]]", "[[Inbox/Note]]", "[[Note.md]]", "![[diagram.png]]"]
)
def test_link_forms(reference):
    docs = vault()
    docs["Inbox/Extra.md"] = reference
    after = apply(docs, prepare(docs))
    assert after["Inbox/Extra.md"].startswith("!") == reference.startswith("!")


def test_handwritten_alias_blocks():
    docs = vault()
    docs["Other/Reference.md"] = "[[Original note]]"
    a = prepare(docs)
    assert a["status"] == "blocked"
    assert any(i["code"] == "link-ambiguous" for i in a["issues"])


@pytest.mark.parametrize(
    "change",
    [
        {"path": "../escape.md"},
        {"old_path": "missing.md"},
        {"record_digest": "sha256:" + "0" * 64},
        {"unknown": True},
    ],
)
def test_invalid_move_arguments(change):
    args = arguments(vault())
    args.update(change)
    result = anyio.run(build_server().call_tool, "kb_prepare_document_move", args)
    assert result.is_error


def test_d05_concurrent_record_reprepare():
    docs = vault()
    server = build_server()
    args = arguments(docs)
    first = invoke(server, args)
    concurrent = records.parse(args["record"])
    concurrent["Other/Reference.md"] = typed()
    args.update(
        record=records.dump(concurrent),
        searched=True,
        search=first["search"],
        documents=[
            {"path": p, "text": t} for p, t in docs.items() if p.endswith(".md")
        ],
    )
    answer = invoke(server, args)
    assert "Other/Reference.md" in records.parse(answer["record"])


def test_d04_external_conflict_retains_original():
    folders = [
        {
            "folder": "decisions",
            "files": [
                {"name": p.name, **header(p.read_text())}
                for p in (BUNDLED / CODEBASE).glob("*.kbp.yaml")
            ],
        }
    ]
    args = arguments(vault())
    a = call(
        build_server(),
        "kb_prepare_document_types",
        dict(
            location="vault",
            record=args["record"],
            changes=[
                dict(change="moved", old_path=args["old_path"], path=args["path"])
            ],
            knowledge_bus_folders=folders,
            allowed_by=PERMISSION,
        ),
    )
    assert a["record"] is None
    assert a["to_settle"][0]["was"]["document_type"] == "decision-record"
    assert a["to_settle"][0]["old_path"] == args["old_path"]


def test_two_call_stdio_session(tmp_path):
    docs = vault()
    args = arguments(docs)

    async def steps(client):
        first = await client.call_tool("kb_prepare_document_move", args)
        assert not first.is_error
        args.update(
            searched=True,
            search=first.structured_content["search"],
            documents=[
                dict(path=p, text=t) for p, t in docs.items() if p.endswith(".md")
            ],
        )
        second = await client.call_tool("kb_prepare_document_move", args)
        assert not second.is_error
        return second.structured_content

    assert session(server_parameters(tmp_path), steps)["status"] == "ready"


def test_new_duplicate_repairs_previously_unique_short_link():
    docs = vault()
    docs["Other/Existing.md"] = "# Existing\n"
    docs["Other/Reference.md"] = "[[Existing|original]] [[Note|moved]]"
    a = prepare(docs, path="decisions/Existing.md")
    after = apply(docs, a)
    assert (
        after["Other/Reference.md"]
        == "[[Other/Existing|original]] [[decisions/Existing|moved]]"
    )


def test_unicode_binding_offsets():
    docs = vault()
    docs["Other/Reference.md"] = "🌟 [[Index]]"
    a = prepare(
        docs,
        bindings=[
            dict(
                source_path="Other/Reference.md",
                start=2,
                end=11,
                target_path="Same/Index.md",
            )
        ],
    )
    assert apply(docs, a)["Other/Reference.md"] == "🌟 [[Same/Index]]"


def test_concurrent_inventory_requires_reprepare():
    docs = vault()
    first = prepare(docs)
    docs["Added.md"] = "New concurrent note.\n"
    second = prepare(docs)
    assert first["based_on"]["listing_digest"] != second["based_on"]["listing_digest"]
    assert "Added.md" in apply(docs, second)


def test_recovery_stops_at_concurrent_change():
    docs = vault()
    plan = prepare(docs)
    first = plan["writes"][0]
    after = apply(docs, {**plan, "writes": [first]})
    after[first["path"]] += "\nConcurrent text.\n"
    assert records.digest(after[first["path"]]) != first["after_digest"]
    assert "Concurrent text." in after[first["path"]]


@pytest.mark.parametrize("text", [r"[escaped](../Inbox/Note\.md)", "[[Note^id]]"])
def test_unsupported_destination_syntax_blocks(text):
    docs = vault()
    docs["Other/Reference.md"] = text
    a = prepare(docs)
    assert a["status"] == "blocked"
    assert any(i["code"] == "link-unsupported" for i in a["issues"])


def test_external_html_is_unchanged():
    docs = vault()
    docs["Other/Reference.md"] = '<a href="https://example.com/Note">External</a>'
    assert (
        apply(docs, prepare(docs))["Other/Reference.md"] == docs["Other/Reference.md"]
    )


PEER_MOVE_PERMISSION = {
    "basis": "request",
    "text": (
        "Fictional QA approval: move Inbox/Note.md to decisions/note.md, update "
        "outside-folder references in References/Index.md, and move its classification "
        "entry while preserving its type, reader and provenance."
    ),
}


@pytest.fixture
def peer_move(
    tmp_path: Path,
) -> tuple[Path, dict[str, str], list[dict[str, Any]], StdioServerParameters]:
    root = tmp_path / "vault"
    copytree(FIXTURE, root)
    original = vault()
    record = records.dump(
        {
            p: typed(
                audience={"value": "future reader", "status": "confirmed"},
                fingerprint=records.digest(original[p]),
            )
            for p in (
                "Inbox/Note.md",
                "decisions/cache-policy.md",
                "decisions/queue-policy.md",
            )
        }
    )
    config = root / records.PLACE
    config.parent.mkdir(parents=True)
    config.write_text(record)
    original[records.PLACE] = record
    listing = [{"path": p} for p in vault()]
    common = dict(location=str(root), knowledge_bus_folders=[], record=record)
    parameters = server_parameters(tmp_path)

    async def preview(client: Client) -> dict[str, Any]:
        result = await client.call_tool(
            "kb_get_document_type",
            dict(
                **common,
                name="Note.md",
                folders=["Inbox"],
                listing=listing,
                conventions_files=[{"folder": "", "text": ""}],
            ),
        )
        assert not result.is_error
        proposal = result.structured_content["filing"][0]["proposal"]
        assert proposal["path"] == "decisions/note.md"
        assert proposal["evidence"] == [
            "decisions/cache-policy.md",
            "decisions/queue-policy.md",
        ]
        args = dict(
            **common,
            old_path="Inbox/Note.md",
            path=proposal["path"],
            listing=listing,
            documents=[{"path": "Inbox/Note.md", "text": original["Inbox/Note.md"]}],
            case_mode="sensitive",
            allowed_by=PEER_MOVE_PERMISSION,
        )
        first = await client.call_tool("kb_prepare_document_move", args)
        assert not first.is_error
        assert first.structured_content["status"] == "texts_needed"
        assert first.structured_content["writes"] == []
        search = first.structured_content["search"]
        documents = []
        searched = []
        for path in sorted(root.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            text = path.read_text()
            searched.append(relative)
            if relative == "Inbox/Note.md" or any(
                term.casefold() in text.casefold() for term in search
            ):
                documents.append({"path": relative, "text": text})
        assert searched == sorted(p for p in vault() if p.endswith(".md"))
        assert "References/Index.md" in [d["path"] for d in documents]
        second = await client.call_tool(
            "kb_prepare_document_move",
            dict(**args, searched=True, search=search) | {"documents": documents},
        )
        assert not second.is_error
        return second.structured_content

    plan = session(parameters, preview)
    assert plan["status"] == "ready", plan["issues"]
    writes = [
        *plan["writes"],
        dict(
            old_path=records.PLACE,
            path=records.PLACE,
            text=plan["record"],
            before_digest=records.digest(record),
            after_digest=records.digest(plan["record"]),
        ),
    ]
    assert {w["old_path"] for w in writes} == {
        "Inbox/Note.md",
        "References/Index.md",
        records.PLACE,
    }
    return root, original, writes, parameters


def apply_peer_move(
    root: Path,
    original: dict[str, str],
    writes: list[dict[str, Any]],
    parameters: StdioServerParameters,
    interrupted: bool,
) -> None:

    async def apply_and_record(client: Client) -> None:
        for index, w in enumerate(writes, 1):
            source, target = root / w["old_path"], root / w["path"]
            assert records.digest(source.read_text()) == w["before_digest"]
            if source != target:
                assert not target.exists()
                with target.open("x") as stream:
                    stream.write(w["text"])
                source.unlink()
            else:
                target.write_text(w["text"])
            result = await client.call_tool(
                "kb_record_edit",
                dict(
                    location=str(root),
                    allowed_by=PEER_MOVE_PERMISSION,
                    before=original[w["old_path"]],
                    after=target.read_text(),
                    whole_file=True,
                    operation=dict(
                        id="peer-move",
                        index=index,
                        count=len(writes),
                        old_path=w["old_path"],
                        path=w["path"],
                    ),
                ),
            )
            assert not result.is_error
            if interrupted and index == 2:
                with pytest.raises(OSError, match="simulated write failure"):
                    fail_write()
                return

    session(parameters, apply_and_record)


def reload_peer_move(
    root: Path,
    original: dict[str, str],
    parameters: StdioServerParameters,
    interrupted: bool,
) -> list[dict[str, Any]]:
    async def reopen(client: Client) -> list[dict[str, Any]]:
        result = await client.call_tool("kb_list_edits", {"location": str(root)})
        assert not result.is_error
        entries = result.structured_content["edits"]
        assert len(entries) == (2 if interrupted else 3)
        assert {e["operation"]["index"] for e in entries} == set(
            range(1, len(entries) + 1)
        )
        assert all(e["operation"]["count"] == 3 for e in entries)
        assert all(e["operation"]["id"] == "peer-move" for e in entries)
        for e in entries:
            assert e["whole_file"] is True
            assert e["allowed_by"] == PEER_MOVE_PERMISSION
            assert e["before"] == original[e["operation"]["old_path"]]
            assert e["after_digest"] == records.digest(
                (root / e["operation"]["path"]).read_text()
            )
        if not interrupted:
            result = await client.call_tool(
                "kb_get_document_type",
                dict(location=str(root), knowledge_bus_folders=[])
                | dict(
                    name="note.md",
                    folders=["decisions"],
                    record=(root / records.PLACE).read_text(),
                    listing=[
                        {"path": p.relative_to(root).as_posix()}
                        for p in root.rglob("*")
                        if p.is_file()
                    ],
                ),
            )
            assert not result.is_error
            kept = result.structured_content["recorded"]["entry"]
            expected = records.parse(original[records.PLACE])["Inbox/Note.md"]
            assert kept == records.plain(expected)
            assert kept["fingerprint"] == records.digest(
                (root / "decisions/note.md").read_text()
            )
        return entries

    return session(parameters, reopen)


@pytest.mark.parametrize("interrupted", [False, True])
def test_peer_move_on_disk_history_reload_and_guarded_recovery(
    tmp_path: Path,
    peer_move: tuple[Path, dict[str, str], list[dict[str, Any]], StdioServerParameters],
    interrupted: bool,
) -> None:
    root, original, writes, parameters = peer_move
    stage = tmp_path / "originals"
    copytree(root, stage)
    apply_peer_move(root, original, writes, parameters, interrupted)
    entries = reload_peer_move(root, original, parameters, interrupted)
    for entry in entries:
        assert entry["before"] == (stage / entry["operation"]["old_path"]).read_text()
        assert entry["before_digest"] == records.digest(entry["before"])
    if interrupted:
        changed = root / "References/Index.md"
        later = changed.read_text() + "\nLater reader edit.\n"
        changed.write_text(later)

        async def fresh_history(client: Client) -> list[dict[str, Any]]:
            result = await client.call_tool("kb_list_edits", {"location": str(root)})
            assert not result.is_error
            return result.structured_content["edits"]

        persisted = session(parameters, fresh_history)
        assert {e["operation"]["index"] for e in persisted} == {1, 2}
        assert all(e["operation"]["count"] == 3 for e in persisted)
        current = {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        conflicts = []
        for entry in sorted(
            persisted, key=lambda e: e["operation"]["index"], reverse=True
        ):
            operation = entry["operation"]
            target = root / operation["path"]
            source = root / operation["old_path"]
            if records.digest(target.read_text()) != entry["after_digest"] or (
                source != target and source.exists()
            ):
                conflicts.append(operation["path"])
        recovery_status = "blocked" if conflicts else "ready"
        # Check the whole group's guard before any inverse file write.
        assert recovery_status == "blocked"
        assert conflicts == ["References/Index.md"]
        assert {
            p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
        } == current
        assert changed.read_text() == later
        assert not (root / "Inbox/Note.md").exists()
        assert (root / "decisions/note.md").read_text() == original["Inbox/Note.md"]
        assert (root / records.PLACE).read_text() == original[records.PLACE]
        assert session(parameters, fresh_history) == persisted == entries
        for p, text in original.items():
            assert (stage / p).read_text() == text
            if p not in {"Inbox/Note.md", "References/Index.md", records.PLACE}:
                assert (root / p).read_text() == text
    else:
        assert not (root / "Inbox/Note.md").exists()
        assert (root / "decisions/note.md").read_text() == original["Inbox/Note.md"]
        expected = original["References/Index.md"].replace(
            "Inbox/Note", "decisions/note"
        )
        expected = expected.replace("[[Note", "[[note")
        expected = expected.replace("`[[note]]`", "`[[Note]]`")
        expected = expected.replace("~~~markdown\n[[note]]", "~~~markdown\n[[Note]]")
        assert (root / "References/Index.md").read_text() == expected
        saved = records.parse((root / records.PLACE).read_text())
        assert "Inbox/Note.md" not in saved
        assert records.plain(saved["decisions/note.md"]) == records.plain(
            records.parse(original[records.PLACE])["Inbox/Note.md"]
        )
        assert saved["decisions/note.md"].fingerprint == records.digest(
            (root / "decisions/note.md").read_text()
        )
        for p, text in original.items():
            if p not in {"Inbox/Note.md", "References/Index.md", records.PLACE}:
                assert (root / p).read_text() == text
