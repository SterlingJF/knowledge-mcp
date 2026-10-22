from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest
import yaml
from mcp.client import Client
from mcp.client.stdio import stdio_client

from knowledge_mcp import bundled
from tests.document_types_harness import (
    LINE,
    RECORD,
    Harness,
    KnowledgeBase,
    fingerprint,
)
from tests.harness import (
    CODEBASE,
    PRODUCT,
    checked,
    server_parameters,
    session,
    texts,
    validator,
)
from tests.test_approved_names_end_to_end import old_record

README = "README.md"
RFC = "docs/rfcs/0042-cache.md"
RFC_RENAMED = "docs/rfcs/0042-caching.md"
PRICING = "docs/product/pricing.md"
PRICING_MOVED = "docs/product/2027/pricing.md"
QUOTE = "vendor-quote.md"
ADR = "docs/adr/0001-use-dolt.md"
ADR_MOVED = "docs/decisions/0001-use-dolt.md"
RUNBOOK = "docs/runbooks/deploy.md"
CHAT_C = "docs/adr/0002-use-sqlite.md"
CHAT_D = "docs/rfcs/0043-queue.md"

CORRECTION = "0042 is a design doc for the product team, not a design proposal."

Pick = tuple[str, str] | None


def offered(answer: dict[str, Any], item: dict[str, Any]) -> set[tuple[str, str]]:
    found = {(c["universe_spec"], c["document_type"]) for c in item["candidates"]}
    every = answer["scopes"][item["scope"]]["every_document_type"] or []
    found |= {
        (group["universe_spec"], k["document_type"])
        for group in every
        for k in group["kinds"]
    }
    return found


def settle(
    answer: dict[str, Any], picks: dict[str, Pick], **extra: dict[str, Any]
) -> list[dict[str, Any]]:
    assert {item["path"] for item in answer["to_settle"]} == set(picks)
    fits = []
    for item in answer["to_settle"]:
        pick = picks[item["path"]]
        if pick is None:
            fits.append(
                {"path": item["path"], "set_by": "agent", "no_document_type": True}
            )
            continue
        assert pick in offered(answer, item), (item["path"], pick)
        fits.append(
            {
                "path": item["path"],
                "set_by": "agent",
                "universe_spec": pick[0],
                "document_type": pick[1],
                **extra.get(item["path"], {}),
            }
        )
    return fits


def entries(base: KnowledgeBase) -> dict[str, dict[str, Any]]:
    assert RECORD in base.paths()
    data = yaml.safe_load(base.read(RECORD) or "")
    validator("document-types").validate(data)
    return data["files"]


def summary(base: KnowledgeBase) -> dict[str, tuple[Any, ...]]:
    return {
        path: (
            "no document type"
            if entry.get("no_document_type")
            else (entry["universe_spec"], entry["document_type"]),
            entry["set_by"],
        )
        for path, entry in entries(base).items()
    }


def changes(answer: dict[str, Any]) -> list[tuple[str, str]]:
    return [(item["change"], item["path"]) for item in answer["changed"]]


@pytest.fixture(params=["local folder", "content only"])
def base(request, tmp_path: Path) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        tmp_path / "codebase" if request.param == "local folder" else None
    )
    knowledge_base.add_universe_specs("", [CODEBASE, PRODUCT])
    for path in (README, RFC, PRICING, QUOTE):
        knowledge_base.write(path, f"# {path}\n")
    return knowledge_base


def two_chats(state: Path, steps: Any) -> Any:
    """Run a separate server process for each chat to test concurrent access."""

    async def main() -> Any:
        async with (
            Client(stdio_client(server_parameters(state)), mode="legacy") as left,
            Client(stdio_client(server_parameters(state)), mode="legacy") as right,
        ):
            return await steps(left, right)

    return anyio.run(main)


async def _first_session(harness, base, client):
    first = await harness.save(client, listing=harness.listing())
    assert first["record"] is None and first["changed"] == []
    reader = {"audience": {"value": "the product lead", "status": "confirmed"}}
    fits = settle(
        first,
        {
            README: (CODEBASE, "readme"),
            RFC: (CODEBASE, "design-proposal"),
            PRICING: (PRODUCT, "design-doc"),
            QUOTE: None,
        },
        **{PRICING: reader},
    )
    settled = await harness.save(client, entries=fits)
    assert sorted(changes(settled)) == sorted(
        ("settled", path) for path in (README, RFC, PRICING, QUOTE)
    )
    assert settled["digest"] == fingerprint(base.read(RECORD))

    base.write(ADR, "# Use Dolt\n")
    created = await harness.save(
        client,
        changes=[{"change": "created", "path": ADR}],
        entries=[
            {
                "path": ADR,
                "set_by": "agent",
                "universe_spec": PRODUCT,
                "document_type": "decision-record",
            }
        ],
    )
    assert changes(created) == [("settled", ADR)]

    base.move(PRICING, PRICING_MOVED)
    base.move(ADR, ADR_MOVED)
    moved = await harness.save(
        client,
        changes=[
            {"change": "moved", "path": PRICING_MOVED, "old_path": PRICING},
            {"change": "moved", "path": ADR_MOVED, "old_path": ADR},
        ],
    )
    assert changes(moved) == [("moved", PRICING_MOVED), ("moved", ADR_MOVED)]
    assert moved["changed"][0]["entry"]["document_type"] == "design-doc"
    assert moved["to_settle"] == []
    assert moved["changed"][1]["entry"]["document_type"] == "decision-record"

    base.delete(QUOTE)
    deleted = await harness.save(client, changes=[{"change": "deleted", "path": QUOTE}])
    assert changes(deleted) == [("deleted", QUOTE)]

    corrected = await harness.save(
        client,
        entries=[
            {
                "path": RFC,
                "set_by": "person",
                "universe_spec": PRODUCT,
                "document_type": "design-doc",
            }
        ],
        allowed_by={"basis": "request", "text": CORRECTION},
    )
    assert changes(corrected) == [("corrected", RFC)]


async def _second_session(harness, client):
    caught = await harness.save(client, listing=harness.listing())
    [rename] = [item for item in caught["changed"] if item["change"] == "moved"]
    assert (rename["path"], rename["old_path"]) == (RFC_RENAMED, RFC)
    assert rename["entry"]["set_by"] == "person"
    assert {c for c in changes(caught) if c[0] != "moved"} == {
        ("fingerprint", ADR_MOVED)
    }
    await harness.save(client, entries=settle(caught, {RUNBOOK: None}))

    reindex = await harness.save(client, recheck=True)
    assert RFC_RENAMED not in {item["path"] for item in reindex["to_settle"]}
    fits = settle(
        reindex,
        {
            README: (CODEBASE, "readme"),
            PRICING_MOVED: (PRODUCT, "design-doc"),
            ADR_MOVED: (PRODUCT, "decision-record"),
            RUNBOOK: None,
        },
    )
    fits.append(
        {
            "path": RFC_RENAMED,
            "set_by": "agent",
            "universe_spec": CODEBASE,
            "document_type": "design-proposal",
        }
    )
    kept = await harness.save(client, entries=fits)
    assert changes(kept) == [("kept", RFC_RENAMED)]
    assert kept["record"] is None


async def _chats(harness, base, left, right):
    read = harness.record()
    base.write(CHAT_C, "# Use SQLite\n")
    base.write(CHAT_D, "# Queue\n")
    c_changes = {
        "changes": [{"change": "created", "path": CHAT_C}],
        "entries": [
            {
                "path": CHAT_C,
                "set_by": "agent",
                "universe_spec": PRODUCT,
                "document_type": "decision-record",
            }
        ],
    }
    d_changes = {
        "changes": [{"change": "created", "path": CHAT_D}],
        "entries": [
            {
                "path": CHAT_D,
                "set_by": "agent",
                "universe_spec": CODEBASE,
                "document_type": "design-proposal",
            }
        ],
    }
    answers: dict[str, dict[str, Any]] = {}

    async def chat(key: str, client: Any, arguments: dict[str, Any]) -> None:
        answers[key] = await harness.update_on(client, read, **arguments)

    async with anyio.create_task_group() as group:
        group.start_soon(chat, "c", left, c_changes)
        group.start_soon(chat, "d", right, d_changes)
    c_answer, d_answer = answers["c"], answers["d"]
    harness.write_record(c_answer["record"])
    assert harness.record() != read
    stale = yaml.safe_load(d_answer["record"])["files"]
    assert CHAT_C not in stale
    again = await harness.update_on(right, harness.record(), **d_changes)
    harness.write_record(again["record"])


def test_record_survives_restarts_and_concurrent_merges(
    base: KnowledgeBase, tmp_path: Path
):
    state = tmp_path / "state"
    harness = Harness(base)
    if base.root is None:
        assert not Path(base.location).exists()
        assert not Path(base.at(RFC)).exists()

    session(
        server_parameters(state), lambda client: _first_session(harness, base, client)
    )
    assert summary(base) == {
        README: ((CODEBASE, "readme"), "agent"),
        RFC: ((PRODUCT, "design-doc"), "person"),
        PRICING_MOVED: ((PRODUCT, "design-doc"), "agent"),
        ADR_MOVED: ((PRODUCT, "decision-record"), "agent"),
    }
    recorded = entries(base)
    assert recorded[RFC]["allowed_by"] == {"basis": "request", "text": CORRECTION}
    assert recorded[README]["allowed_by"] == {
        "basis": "instruction",
        "text": LINE,
        "location": "AGENTS.md",
    }
    assert recorded[PRICING_MOVED]["audience"] == {
        "value": "the product lead",
        "status": "confirmed",
    }
    assert recorded[RFC]["version"] == "0.9"

    # Change files between sessions to test discovery without reported changes.
    base.move(RFC, RFC_RENAMED)
    base.write(RUNBOOK, "# Deploy\n")

    session(server_parameters(state), lambda client: _second_session(harness, client))
    assert summary(base)[RFC_RENAMED] == ((PRODUCT, "design-doc"), "person")
    assert summary(base)[RUNBOOK] == ("no document type", "agent")
    assert RFC not in summary(base)

    two_chats(state, lambda left, right: _chats(harness, base, left, right))
    final = summary(base)
    assert final[CHAT_C] == ((PRODUCT, "decision-record"), "agent")
    assert final[CHAT_D] == ((CODEBASE, "design-proposal"), "agent")
    assert final[RFC_RENAMED] == ((PRODUCT, "design-doc"), "person")
    assert set(final) == {
        README,
        RFC_RENAMED,
        PRICING_MOVED,
        ADR_MOVED,
        RUNBOOK,
        CHAT_C,
        CHAT_D,
    }

    log = [
        json.loads(line)
        for line in (state / "knowledge-mcp" / "log.jsonl").read_text().splitlines()
    ]
    # Concurrent responses can reach the log in either order.
    assert sorted(json.dumps(entry["returned"]) for entry in log) == sorted(
        json.dumps(texts(result)) for _, _, result in harness.calls
    )
    assert len(log) == len(harness.calls)
    assert {entry["tool"] for entry in log} == {"kb_prepare_document_types"}
    assert {entry["location"] for entry in log} == {base.location}
    for _, _, result in harness.calls:
        checked(result, "document-types-update")


def test_stale_listing_retry_preserves_concurrent_creates_and_deletes(
    base: KnowledgeBase, tmp_path: Path
):
    state = tmp_path / "state"
    harness = Harness(base)

    async def first_session(client):
        first = await harness.save(client, listing=harness.listing())
        reader = {"audience": {"value": "the product lead", "status": "confirmed"}}
        picks: dict[str, Pick] = {
            README: (CODEBASE, "readme"),
            RFC: (CODEBASE, "design-proposal"),
            PRICING: (PRODUCT, "design-doc"),
            QUOTE: None,
        }
        await harness.save(client, entries=settle(first, picks, **{PRICING: reader}))

    session(server_parameters(state), first_session)

    base.move(PRICING, PRICING_MOVED)
    base.write(README, "# README, edited\n")

    async def chats(left, right):
        read = harness.record()
        listing = harness.listing()
        base.write(CHAT_C, "# Use SQLite\n")
        base.delete(QUOTE)
        await harness.save(
            left,
            changes=[
                {"change": "created", "path": CHAT_C},
                {"change": "deleted", "path": QUOTE},
            ],
            entries=[
                {
                    "path": CHAT_C,
                    "set_by": "agent",
                    "universe_spec": PRODUCT,
                    "document_type": "decision-record",
                }
            ],
        )
        return await harness.save_from(right, read, listing=listing)

    final = two_chats(state, chats)

    first_d, again_d = [args for _, args, _ in harness.calls][-2:]
    assert "listing" in first_d and "listing" not in again_d
    [first_answer] = texts(harness.calls[-2][2])
    assert json.loads(first_answer)["listing_changes"] == [
        {
            "change": "moved",
            "path": PRICING_MOVED,
            "old_path": PRICING,
            "fingerprint": fingerprint(f"# {PRICING}\n"),
        },
        {
            "change": "edited",
            "path": README,
            "fingerprint": fingerprint("# README, edited\n"),
        },
    ]
    assert again_d["changes"] == json.loads(first_answer)["listing_changes"]
    assert ("deleted", CHAT_C) not in changes(final)
    assert final["to_settle"] == []
    recorded = entries(base)
    assert set(recorded) == {README, RFC, PRICING_MOVED, CHAT_C}
    assert recorded[CHAT_C]["document_type"] == "decision-record"
    assert recorded[PRICING_MOVED]["audience"]["status"] == "confirmed"
    assert recorded[README]["fingerprint"] == fingerprint("# README, edited\n")
    for _, _, result in harness.calls:
        checked(result, "document-types-update")


def test_kb_get_document_type_returns_recorded_fit_and_no_fit(
    base: KnowledgeBase, tmp_path: Path
):
    harness = Harness(base)

    async def steps(client):
        first = await harness.save(client, listing=harness.listing())
        fits = settle(
            first,
            {
                README: (CODEBASE, "readme"),
                RFC: (CODEBASE, "design-proposal"),
                PRICING: (PRODUCT, "design-doc"),
                QUOTE: None,
            },
        )
        await harness.save(client, entries=fits)
        text = harness.record()

        def ask(path: str, **record: str) -> Any:
            folder, _, name = path.rpartition("/")
            return harness.call(
                client,
                "kb_get_document_type",
                {
                    "location": base.at(path),
                    "name": name,
                    "folders": folder.split("/") if folder else [],
                    "knowledge_bus_folders": [
                        {"folder": "", "files": harness.universe_specs()[0]["files"]}
                    ],
                    **record,
                },
            )

        quote = await ask(QUOTE, record=text)
        digest = checked(quote, "document-type")["received"][-1]["digest"]
        rfc = await ask(RFC, record_digest=digest)
        unrecorded = await ask("docs/rfcs/0099-new.md", record_digest=digest)
        unknown = await ask(RFC, record_digest="sha256:" + "0" * 64)
        return quote, rfc, unrecorded, unknown

    quote, rfc, unrecorded, unknown = session(
        server_parameters(tmp_path / "state"), steps
    )

    quote_answer = checked(quote, "document-type")
    assert quote_answer["recorded"]["label"] == "from the document-types file"
    assert quote_answer["recorded"]["entry"]["no_document_type"] is True
    assert quote_answer["recorded"]["path"] == QUOTE
    assert (
        quote_answer["candidates"] == [] and quote_answer["every_document_type"] is None
    )
    assert quote_answer["received"][-1]["name"] == RECORD

    rfc_answer = checked(rfc, "document-type")
    assert rfc_answer["recorded"]["label"] == "from the document-types file"
    assert (
        rfc_answer["recorded"]["entry"]["universe_spec"],
        rfc_answer["recorded"]["entry"]["document_type"],
    ) == (
        CODEBASE,
        "design-proposal",
    )
    assert {spec["source"] for spec in rfc_answer["universe_specs"]} == {
        f"bundled copy at {bundled.ref()}"
    }

    unrecorded_answer = checked(unrecorded, "document-type")
    assert "recorded" not in unrecorded_answer
    assert unrecorded_answer["candidates"]

    assert unknown.is_error and "Send `record`" in texts(unknown)[0]


def test_kb_get_document_type_applies_pending_moves_and_deletions_without_writing_record(
    base: KnowledgeBase, tmp_path: Path
):
    harness = Harness(base)

    async def steps(client):
        first = await harness.save(client, listing=harness.listing())
        fits = settle(
            first,
            {
                README: (CODEBASE, "readme"),
                RFC: (CODEBASE, "design-proposal"),
                PRICING: (PRODUCT, "design-doc"),
                QUOTE: None,
            },
        )
        for item in fits:
            if item["path"] == RFC:
                item["set_by"] = "person"
        await harness.save(client, entries=fits)
        text = harness.record()

        def ask(path: str, changes: list[dict[str, str]]) -> Any:
            folder, _, name = path.rpartition("/")
            return harness.call(
                client,
                "kb_get_document_type",
                {
                    "location": base.at(path),
                    "name": name,
                    "folders": folder.split("/") if folder else [],
                    "knowledge_bus_folders": [
                        {"folder": "", "files": harness.universe_specs()[0]["files"]}
                    ],
                    "record": text,
                    "changes": changes,
                },
            )

        renamed = await ask(
            RFC_RENAMED, [{"change": "moved", "path": RFC_RENAMED, "old_path": RFC}]
        )
        old = await ask(
            RFC, [{"change": "moved", "path": RFC_RENAMED, "old_path": RFC}]
        )
        moved = await ask(
            PRICING_MOVED,
            [{"change": "moved", "path": PRICING_MOVED, "old_path": PRICING}],
        )
        deleted = await ask(QUOTE, [{"change": "deleted", "path": QUOTE}])
        alone = await harness.call(
            client,
            "kb_get_document_type",
            {
                "location": base.at(QUOTE),
                "name": QUOTE,
                "folders": [],
                "knowledge_bus_folders": [],
                "changes": [{"change": "deleted", "path": QUOTE}],
            },
        )
        return text, renamed, old, moved, deleted, alone

    text, renamed, old, moved, deleted, alone = session(
        server_parameters(tmp_path / "state"), steps
    )

    renamed_answer = checked(renamed, "document-type")
    assert renamed_answer["recorded"]["path"] == RFC_RENAMED
    assert renamed_answer["recorded"]["entry"]["set_by"] == "person"
    assert "recorded" not in checked(old, "document-type")
    moved_answer = checked(moved, "document-type")
    assert moved_answer["recorded"]["entry"]["document_type"] == "design-doc"
    assert moved_answer["candidates"] == []
    assert moved_answer["every_document_type"] is None
    assert "recorded" not in checked(deleted, "document-type")
    assert alone.is_error and "with `changes`" in texts(alone)[0]
    assert harness.record() == text


BUNDLED_SOURCE = f"bundled copy at {bundled.ref()}"
NESTED_RFC = "team/rfcs/0042-cache.md"
NESTED_NEW = "team/rfcs/0043-queue.md"
GUIDE = "guide/README.md"


@pytest.fixture(params=["local folder", "content only"])
def bare(request, tmp_path: Path) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        tmp_path / "plain" if request.param == "local folder" else None
    )
    for path in (README, QUOTE):
        knowledge_base.write(path, f"# {path}\n")
    return knowledge_base


def fit_call(harness: Harness, path: str) -> dict[str, Any]:
    folder, _, name = path.rpartition("/")
    folders = folder.split("/") if folder else []
    specs = []
    for item in harness.universe_specs():
        parts = item["folder"].split("/") if item["folder"] else []
        if folders[: len(parts)] == parts:
            specs.append(item)
    return {
        "location": harness.base.at(path),
        "name": name,
        "folders": folders,
        "knowledge_bus_folders": specs,
    }


def test_record_only_scope_uses_bundled_universe_specs(
    bare: KnowledgeBase, tmp_path: Path
):
    harness = Harness(bare)

    async def steps(client):
        first = await harness.save(client, listing=harness.listing())
        await harness.save(
            client,
            entries=settle(first, {README: (CODEBASE, "readme"), QUOTE: None}),
        )
        bare.write(GUIDE, "# Guide\n")
        readme = await harness.call(
            client, "kb_get_document_type", fit_call(harness, README)
        )
        later = await harness.save(client, listing=harness.listing())
        return first, readme, later

    first, readme, later = session(server_parameters(tmp_path / "state"), steps)

    assert first["scopes"][0]["universe_specs"]
    assert set(entries(bare)) == {README, QUOTE}
    assert harness.universe_specs() == [{"folder": "", "files": []}]
    answer = checked(readme, "document-type")
    assert (
        answer["candidates"][0]["universe_spec"],
        answer["candidates"][0]["document_type"],
    ) == (
        CODEBASE,
        "readme",
    )
    assert {spec["source"] for spec in answer["universe_specs"]} == {BUNDLED_SOURCE}
    [waiting] = later["to_settle"]
    assert waiting["path"] == GUIDE
    assert (CODEBASE, "readme") in offered(later, waiting)
    scope = later["scopes"][waiting["scope"]]["universe_specs"]
    assert {spec["id"] for spec in scope} == {CODEBASE, PRODUCT}
    assert {spec["source"] for spec in scope} == {BUNDLED_SOURCE}
    assert later["listing_changes"] == [
        {"change": "created", "path": GUIDE, "fingerprint": fingerprint("# Guide\n")}
    ]


def test_a_nested_folder_keeps_its_own_scope_below_a_record_only_top_folder(
    bare: KnowledgeBase, tmp_path: Path
):
    bare.add_universe_specs("team", [PRODUCT])
    bare.write(NESTED_RFC, "# Cache\n")
    harness = Harness(bare)

    async def steps(client):
        first = await harness.save(client, listing=harness.listing())
        await harness.save(
            client,
            entries=settle(
                first,
                {
                    README: (CODEBASE, "readme"),
                    QUOTE: None,
                    NESTED_RFC: (PRODUCT, "design-doc"),
                },
            ),
        )
        bare.write(NESTED_NEW, "# Queue\n")
        nested = await harness.call(
            client, "kb_get_document_type", fit_call(harness, NESTED_NEW)
        )
        later = await harness.save(client, listing=harness.listing())
        return nested, later

    nested, later = session(server_parameters(tmp_path / "state"), steps)

    assert [item["folder"] for item in harness.universe_specs()] == ["", "team"]
    answer = checked(nested, "document-type")
    assert [(c["universe_spec"], c["document_type"]) for c in answer["candidates"]] == [
        (PRODUCT, "design-doc")
    ]
    assert [(s["id"], s["from_parent"]) for s in answer["universe_specs"]] == [
        (PRODUCT, False)
    ]
    [waiting] = later["to_settle"]
    assert waiting["path"] == NESTED_NEW
    assert [
        (spec["id"], spec["from_parent"])
        for spec in later["scopes"][waiting["scope"]]["universe_specs"]
    ] == [(PRODUCT, False)]
    assert entries(bare)[NESTED_RFC]["universe_spec"] == PRODUCT


def test_physical_shared_record_serialized_writers_preserve_complete_metadata(tmp_path):
    """Two clients share a physical record; test code serializes saves, not a server lock."""
    base = KnowledgeBase(tmp_path / "base")
    base.add_universe_specs("", [CODEBASE, PRODUCT])
    base.write(PRICING, "# Pricing\r\n")
    base.write(RFC, "# Cache\r\n")
    base.write("review.md", "# Saved next steps\r\n\r\nQuestion still open.\r\n")
    authority = {
        "basis": "request",
        "text": "Pricing is a design doc for the product lead.",
    }
    original = {
        "universe_spec": PRODUCT,
        "version": "0.9",
        "document_type": "design-doc",
        "set_by": "person",
        "allowed_by": authority,
        "time": "2026-10-10T09:16:40.003Z",
        "audience": {"value": "the product lead", "status": "confirmed"},
    }
    # Carry a canonical legacy fixture entry through a physical migration save.
    legacy = yaml.safe_load(old_record())
    legacy["files"] = {PRICING: legacy["files"][PRICING]}
    legacy_text = yaml.safe_dump(legacy).replace("\n", "\r\n")
    old_path = ".knowledge-bus/plugins/knowledge-mcp/record.yaml"
    base.write(old_path, legacy_text)
    migration_harness = Harness(base)
    state = tmp_path / "state"
    migrated = session(
        server_parameters(state),
        lambda client: migration_harness.update_on(client, legacy_text),
    )
    assert not (base.root / RECORD).exists()
    migration_harness.write_record(migrated["record"])
    assert yaml.safe_load(base.read(RECORD))["files"] == {PRICING: original}
    assert (base.root / old_path).read_bytes() == legacy_text.encode()
    left, right = Harness(base), Harness(KnowledgeBase(base.root))
    assert left.base.root / RECORD == right.base.root / RECORD
    old = left.record()
    before_note = (base.root / "review.md").read_bytes()
    left_changes = {
        "entries": [
            {
                "path": RFC,
                "set_by": "agent",
                "universe_spec": CODEBASE,
                "document_type": "design-proposal",
            }
        ]
    }
    right_changes = {
        "entries": [{"path": QUOTE, "set_by": "agent", "no_document_type": True}]
    }

    async def prepare(client):
        return await left.update_on(client, old, **left_changes)

    first = session(server_parameters(state), prepare)
    first_rfc = yaml.safe_load(first["record"])["files"][RFC]
    # Preparation itself must never write the shared settings or notes.
    assert left.record() == old
    stale = session(
        server_parameters(state),
        lambda client: right.update_on(client, old, **right_changes),
    )
    assert first["based_on"] == fingerprint(old) == stale["based_on"]
    left.write_record(first["record"])
    assert fingerprint(right.record()) != stale["based_on"]
    # Reread/reprepare from another process before its serialized save.
    second = session(
        server_parameters(state), lambda client: right.save(client, **right_changes)
    )
    assert second["based_on"] == fingerprint(first["record"])
    actual = yaml.safe_load((base.root / RECORD).read_bytes())
    assert actual["schema"] == "knowledge-mcp/document-types/1"
    assert set(actual["files"]) == {PRICING, RFC, QUOTE}
    assert actual["files"][PRICING] == original
    assert actual["files"][RFC] == first_rfc
    for path, kind in ((RFC, "design-proposal"), (QUOTE, None)):
        item = actual["files"][path]
        expected = {
            "set_by": "agent",
            "allowed_by": {
                "basis": "instruction",
                "text": LINE,
                "location": "AGENTS.md",
            },
            "time": item["time"],
        }
        if kind:
            expected.update(universe_spec=CODEBASE, version="0.1", document_type=kind)
        else:
            expected["no_document_type"] = True
        assert item == expected
    assert (base.root / "review.md").read_bytes() == before_note
    assert (base.root / PRICING).read_bytes() == b"# Pricing\r\n"
