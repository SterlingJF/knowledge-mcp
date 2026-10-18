from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import anyio
import pytest

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
