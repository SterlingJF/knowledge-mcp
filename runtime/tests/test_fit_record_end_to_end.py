"""The fit record kept across sessions and simultaneous chats, through the stdio server.

Each session is its own server process, as each chat in a host starts its own. The host reads
and writes `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, creating the folders when
missing; knowledge-mcp only merges.
"""

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
from tests.hosts import (
    CODEBASE,
    PRODUCT,
    checked,
    server_parameters,
    session,
    texts,
    validator,
)
from tests.record_host import LINE, RECORD, Host, KnowledgeBase, fingerprint

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
    """The document types the answer offers for a file waiting to be settled."""
    found = {(c["universe_spec"], c["kind"]) for c in item["candidates"]}
    every = answer["scopes"][item["scope"]]["every_document_type"] or []
    found |= {
        (group["universe_spec"], k["kind"]) for group in every for k in group["kinds"]
    }
    return found


def settle(
    answer: dict[str, Any], picks: dict[str, Pick], **extra: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build one fit for each pending file; each selected document type must be
    available in the response.
    """
    assert {item["path"] for item in answer["to_settle"]} == set(picks)
    fits = []
    for item in answer["to_settle"]:
        pick = picks[item["path"]]
        if pick is None:
            fits.append({"path": item["path"], "made": "fit", "no_fit": True})
            continue
        assert pick in offered(answer, item), (item["path"], pick)
        fits.append(
            {
                "path": item["path"],
                "made": "fit",
                "universe_spec": pick[0],
                "kind": pick[1],
                **extra.get(item["path"], {}),
            }
        )
    return fits


def entries(base: KnowledgeBase) -> dict[str, dict[str, Any]]:
    """Validate the saved record against its schema and return its file entries."""
    assert RECORD in base.paths()
    data = yaml.safe_load(base.read(RECORD) or "")
    validator("fit-record").validate(data)
    return data["files"]


def summary(base: KnowledgeBase) -> dict[str, tuple[Any, ...]]:
    """Each recorded file's fit and how its entry was made."""
    return {
        path: (
            "no fit"
            if entry.get("no_fit")
            else (entry["universe_spec"], entry["kind"]),
            entry["made"],
        )
        for path, entry in entries(base).items()
    }


def changes(answer: dict[str, Any]) -> list[tuple[str, str]]:
    return [(item["change"], item["path"]) for item in answer["changed"]]


@pytest.fixture(params=["local folder", "content only"])
def base(request, tmp_path: Path) -> KnowledgeBase:
    """A codebase with both bundled universe specs, on disk or reachable only as content."""
    knowledge_base = KnowledgeBase(
        tmp_path / "codebase" if request.param == "local folder" else None
    )
    knowledge_base.add_universe_specs("", [CODEBASE, PRODUCT])
    for path in (README, RFC, PRICING, QUOTE):
        knowledge_base.write(path, f"# {path}\n")
    return knowledge_base


def two_chats(state: Path, steps: Any) -> Any:
    """Two server processes running at once, one per chat."""

    async def main() -> Any:
        async with (
            Client(stdio_client(server_parameters(state)), mode="legacy") as left,
            Client(stdio_client(server_parameters(state)), mode="legacy") as right,
        ):
            return await steps(left, right)

    return anyio.run(main)


def test_record_survives_restarts_and_concurrent_merges(
    base: KnowledgeBase, tmp_path: Path
):
    state = tmp_path / "state"
    host = Host(base)
    if base.root is None:
        # Content-only locations are Drive URLs without corresponding local paths.
        assert not Path(base.location).exists()
        assert not Path(base.at(RFC)).exists()

    # Session 1: the first call compares the listing with a missing record.
    async def first_session(client):
        first = await host.save(client, listing=host.listing())
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
        settled = await host.save(client, fits=fits)
        assert sorted(changes(settled)) == sorted(
            ("fitted", path) for path in (README, RFC, PRICING, QUOTE)
        )
        assert settled["digest"] == fingerprint(base.read(RECORD))

        # The agent writes a new decision record, then records the new file and its fit.
        base.write(ADR, "# Use Dolt\n")
        created = await host.save(
            client,
            changes=[{"change": "created", "path": ADR}],
            fits=[
                {
                    "path": ADR,
                    "made": "fit",
                    "universe_spec": PRODUCT,
                    "kind": "decision-record",
                }
            ],
        )
        assert changes(created) == [("fitted", ADR)]

        # Moving a file preserves its confirmed audience; a plain fit must be settled again.
        base.move(PRICING, PRICING_MOVED)
        base.move(ADR, ADR_MOVED)
        moved = await host.save(
            client,
            changes=[
                {"change": "moved", "path": PRICING_MOVED, "old_path": PRICING},
                {"change": "moved", "path": ADR_MOVED, "old_path": ADR},
            ],
        )
        assert changes(moved) == [("moved", PRICING_MOVED), ("moved", ADR_MOVED)]
        assert moved["changed"][0]["entry"]["kind"] == "design-doc"
        [waiting] = moved["to_settle"]
        assert (waiting["path"], waiting["old_path"]) == (ADR_MOVED, ADR)
        assert waiting["was"]["kind"] == "decision-record"
        resettled = await host.save(
            client, fits=settle(moved, {ADR_MOVED: (PRODUCT, "decision-record")})
        )
        assert changes(resettled) == [("fitted", ADR_MOVED)]

        base.delete(QUOTE)
        deleted = await host.save(
            client, changes=[{"change": "deleted", "path": QUOTE}]
        )
        assert changes(deleted) == [("deleted", QUOTE)]

        # The person corrects the agent's fit.
        corrected = await host.save(
            client,
            fits=[
                {
                    "path": RFC,
                    "made": "correction",
                    "universe_spec": PRODUCT,
                    "kind": "design-doc",
                }
            ],
            basis="request",
            basis_text=CORRECTION,
            basis_location=None,
        )
        assert changes(corrected) == [("corrected", RFC)]

    session(server_parameters(state), first_session)
    assert summary(base) == {
        README: ((CODEBASE, "readme"), "fit"),
        RFC: ((PRODUCT, "design-doc"), "correction"),
        PRICING_MOVED: ((PRODUCT, "design-doc"), "fit"),
        ADR_MOVED: ((PRODUCT, "decision-record"), "fit"),
    }
    recorded = entries(base)
    assert recorded[RFC]["allowed_by"] == {"basis": "request", "text": CORRECTION}
    assert recorded[README]["allowed_by"] == {
        "basis": "line",
        "text": LINE,
        "location": "AGENTS.md",
    }
    assert recorded[PRICING_MOVED]["audience"] == {
        "value": "the product lead",
        "status": "confirmed",
    }
    assert recorded[RFC]["version"] == "0.9"

    # Between sessions, someone renames a file and adds another, outside the agent.
    base.move(RFC, RFC_RENAMED)
    base.write(RUNBOOK, "# Deploy\n")

    # The new server process detects the rename and creation from the listing.
    async def second_session(client):
        caught = await host.save(client, listing=host.listing())
        [rename] = [item for item in caught["changed"] if item["change"] == "moved"]
        assert (rename["path"], rename["old_path"]) == (RFC_RENAMED, RFC)
        assert rename["entry"]["made"] == "correction"
        # The listing supplies the missing fingerprint for the moved decision record.
        assert {c for c in changes(caught) if c[0] != "moved"} == {
            ("fingerprint", ADR_MOVED)
        }
        await host.save(client, fits=settle(caught, {RUNBOOK: None}))

        # Refit queues uncorrected files; later agent fits preserve the recorded correction.
        reindex = await host.save(client, refit=True)
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
                "made": "fit",
                "universe_spec": CODEBASE,
                "kind": "design-proposal",
            }
        )
        kept = await host.save(client, fits=fits)
        # Repeated fits preserve the saved record and report the retained correction as `kept`.
        assert changes(kept) == [("kept", RFC_RENAMED)]
        assert kept["record"] is None

    session(server_parameters(state), second_session)
    assert summary(base)[RFC_RENAMED] == ((PRODUCT, "design-doc"), "correction")
    assert summary(base)[RUNBOOK] == ("no fit", "fit")
    assert RFC not in summary(base)

    # Two chats at once, each a server process, both starting from the same record.
    async def chats(left, right):
        read = host.record()
        base.write(CHAT_C, "# Use SQLite\n")
        base.write(CHAT_D, "# Queue\n")
        c_changes = {
            "changes": [{"change": "created", "path": CHAT_C}],
            "fits": [
                {
                    "path": CHAT_C,
                    "made": "fit",
                    "universe_spec": PRODUCT,
                    "kind": "decision-record",
                }
            ],
        }
        d_changes = {
            "changes": [{"change": "created", "path": CHAT_D}],
            "fits": [
                {
                    "path": CHAT_D,
                    "made": "fit",
                    "universe_spec": CODEBASE,
                    "kind": "design-proposal",
                }
            ],
        }
        answers: dict[str, dict[str, Any]] = {}

        async def chat(key: str, client: Any, arguments: dict[str, Any]) -> None:
            answers[key] = await host.update_on(client, read, **arguments)

        async with anyio.create_task_group() as group:
            group.start_soon(chat, "c", left, c_changes)
            group.start_soon(chat, "d", right, d_changes)
        c_answer, d_answer = answers["c"], answers["d"]
        host.write_record(c_answer["record"])
        # Chat D reads the file again right before writing, sees chat C's save, and merges again.
        assert host.record() != read
        stale = yaml.safe_load(d_answer["record"])["files"]
        assert CHAT_C not in stale
        again = await host.update_on(right, host.record(), **d_changes)
        host.write_record(again["record"])

    two_chats(state, chats)
    final = summary(base)
    assert final[CHAT_C] == ((PRODUCT, "decision-record"), "fit")
    assert final[CHAT_D] == ((CODEBASE, "design-proposal"), "fit")
    assert final[RFC_RENAMED] == ((PRODUCT, "design-doc"), "correction")
    assert set(final) == {
        README,
        RFC_RENAMED,
        PRICING_MOVED,
        ADR_MOVED,
        RUNBOOK,
        CHAT_C,
        CHAT_D,
    }

    # The log contains one returned-answer entry per call across all sessions.
    log = [
        json.loads(line)
        for line in (state / "knowledge-mcp" / "log.jsonl").read_text().splitlines()
    ]
    # The two chats answered at once, so their lines can come in either order.
    assert sorted(json.dumps(entry["returned"]) for entry in log) == sorted(
        json.dumps(texts(result)) for _, _, result in host.calls
    )
    assert len(log) == len(host.calls)
    assert {entry["tool"] for entry in log} == {"kb_fit_record"}
    assert {entry["location"] for entry in log} == {base.location}
    for _, _, result in host.calls:
        checked(result, "fit-record-update")


def test_stale_listing_retry_preserves_concurrent_creates_and_deletes(
    base: KnowledgeBase, tmp_path: Path
):
    state = tmp_path / "state"
    host = Host(base)

    async def first_session(client):
        first = await host.save(client, listing=host.listing())
        reader = {"audience": {"value": "the product lead", "status": "confirmed"}}
        picks: dict[str, Pick] = {
            README: (CODEBASE, "readme"),
            RFC: (CODEBASE, "design-proposal"),
            PRICING: (PRODUCT, "design-doc"),
            QUOTE: None,
        }
        await host.save(client, fits=settle(first, picks, **{PRICING: reader}))

    session(server_parameters(state), first_session)

    # Between sessions, someone renames a file and edits another, outside the agent.
    base.move(PRICING, PRICING_MOVED)
    base.write(README, "# README, edited\n")

    async def chats(left, right):
        # Chat D reads the record and lists the files as its session starts.
        read = host.record()
        listing = host.listing()
        # Chat C creates a file, deletes another, and saves first.
        base.write(CHAT_C, "# Use SQLite\n")
        base.delete(QUOTE)
        await host.save(
            left,
            changes=[
                {"change": "created", "path": CHAT_C},
                {"change": "deleted", "path": QUOTE},
            ],
            fits=[
                {
                    "path": CHAT_C,
                    "made": "fit",
                    "universe_spec": PRODUCT,
                    "kind": "decision-record",
                }
            ],
        )
        # Chat D sends its session-start listing and the record snapshot read before chat C saved.
        return await host.save_from(right, read, listing=listing)

    final = two_chats(state, chats)

    # Chat D merged twice: on its listing, then on chat C's save with the listing's changes.
    first_d, again_d = [args for _, args, _ in host.calls][-2:]
    assert "listing" in first_d and "listing" not in again_d
    [first_answer] = texts(host.calls[-2][2])
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
    # Chat C's new file stays, and chat C's deleted file stays out of the record.
    assert ("deleted", CHAT_C) not in changes(final)
    assert final["to_settle"] == []
    recorded = entries(base)
    assert set(recorded) == {README, RFC, PRICING_MOVED, CHAT_C}
    assert recorded[CHAT_C]["kind"] == "decision-record"
    assert recorded[PRICING_MOVED]["audience"]["status"] == "confirmed"
    assert recorded[README]["fingerprint"] == fingerprint("# README, edited\n")
    for _, _, result in host.calls:
        checked(result, "fit-record-update")


def test_kb_fit_returns_recorded_fit_and_no_fit(base: KnowledgeBase, tmp_path: Path):
    host = Host(base)

    async def steps(client):
        first = await host.save(client, listing=host.listing())
        fits = settle(
            first,
            {
                README: (CODEBASE, "readme"),
                RFC: (CODEBASE, "design-proposal"),
                PRICING: (PRODUCT, "design-doc"),
                QUOTE: None,
            },
        )
        await host.save(client, fits=fits)
        text = host.record()

        def ask(path: str, **record: str) -> Any:
            folder, _, name = path.rpartition("/")
            return host.call(
                client,
                "kb_fit",
                {
                    "location": base.at(path),
                    "name": name,
                    "folders": folder.split("/") if folder else [],
                    "universe_specs": [
                        {"depth": 0, "files": host.universe_specs()[0]["files"]}
                    ],
                    **record,
                },
            )

        quote = await ask(QUOTE, record=text)
        digest = checked(quote, "fit")["received"][-1]["digest"]
        rfc = await ask(RFC, record_digest=digest)
        unrecorded = await ask("docs/rfcs/0099-new.md", record_digest=digest)
        unknown = await ask(RFC, record_digest="sha256:" + "0" * 64)
        return quote, rfc, unrecorded, unknown

    quote, rfc, unrecorded, unknown = session(
        server_parameters(tmp_path / "state"), steps
    )

    quote_answer = checked(quote, "fit")
    assert quote_answer["recorded"]["label"] == "from the record"
    assert quote_answer["recorded"]["no_fit"] is True
    assert quote_answer["recorded"]["path"] == QUOTE
    assert (
        quote_answer["candidates"] == [] and quote_answer["every_document_type"] is None
    )
    assert quote_answer["received"][-1]["name"] == RECORD

    rfc_answer = checked(rfc, "fit")
    assert rfc_answer["recorded"]["label"] == "from the record"
    assert (
        rfc_answer["recorded"]["universe_spec"],
        rfc_answer["recorded"]["kind"],
    ) == (
        CODEBASE,
        "design-proposal",
    )
    assert {spec["source"] for spec in rfc_answer["universe_specs"]} == {
        f"bundled copy at {bundled.ref()}"
    }

    unrecorded_answer = checked(unrecorded, "fit")
    assert "recorded" not in unrecorded_answer
    assert unrecorded_answer["candidates"]

    assert unknown.is_error and "send the text" in texts(unknown)[0]


def test_kb_fit_applies_pending_moves_and_deletions_without_writing_record(
    base: KnowledgeBase, tmp_path: Path
):
    host = Host(base)

    async def steps(client):
        first = await host.save(client, listing=host.listing())
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
                item["made"] = "correction"
        await host.save(client, fits=fits)
        text = host.record()

        def ask(path: str, changes: list[dict[str, str]]) -> Any:
            folder, _, name = path.rpartition("/")
            return host.call(
                client,
                "kb_fit",
                {
                    "location": base.at(path),
                    "name": name,
                    "folders": folder.split("/") if folder else [],
                    "universe_specs": [
                        {"depth": 0, "files": host.universe_specs()[0]["files"]}
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
        alone = await host.call(
            client,
            "kb_fit",
            {
                "location": base.at(QUOTE),
                "name": QUOTE,
                "folders": [],
                "universe_specs": [],
                "changes": [{"change": "deleted", "path": QUOTE}],
            },
        )
        return text, renamed, old, moved, deleted, alone

    text, renamed, old, moved, deleted, alone = session(
        server_parameters(tmp_path / "state"), steps
    )

    # The recorded correction follows the rename before the host saves the record.
    renamed_answer = checked(renamed, "fit")
    assert renamed_answer["recorded"]["path"] == RFC_RENAMED
    assert renamed_answer["recorded"]["made"] == "correction"
    assert "recorded" not in checked(old, "fit")
    # A moved plain fit returns candidates or all document types for refitting.
    moved_answer = checked(moved, "fit")
    assert "recorded" not in moved_answer
    assert moved_answer["candidates"] or moved_answer["every_document_type"]
    assert "recorded" not in checked(deleted, "fit")
    assert alone.is_error and "with `changes`" in texts(alone)[0]
    assert host.record() == text


BUNDLED_SOURCE = f"bundled copy at {bundled.ref()}"
NESTED_RFC = "team/rfcs/0042-cache.md"
NESTED_NEW = "team/rfcs/0043-queue.md"
GUIDE = "guide/README.md"


@pytest.fixture(params=["local folder", "content only"])
def bare(request, tmp_path: Path) -> KnowledgeBase:
    """A knowledge base with no `.knowledge-bus/` until the record is saved."""
    knowledge_base = KnowledgeBase(
        tmp_path / "plain" if request.param == "local folder" else None
    )
    for path in (README, QUOTE):
        knowledge_base.write(path, f"# {path}\n")
    return knowledge_base


def fit_call(host: Host, path: str) -> dict[str, Any]:
    """`kb_fit` arguments for `path`, with every `.knowledge-bus/` on its chain."""
    folder, _, name = path.rpartition("/")
    folders = folder.split("/") if folder else []
    specs = []
    for item in host.universe_specs():
        parts = item["folder"].split("/") if item["folder"] else []
        if folders[: len(parts)] == parts:
            specs.append({**item, "depth": len(parts)})
            del specs[-1]["folder"]
    return {
        "location": host.base.at(path),
        "name": name,
        "folders": folders,
        "universe_specs": specs,
    }


def test_record_only_scope_uses_bundled_universe_specs(
    bare: KnowledgeBase, tmp_path: Path
):
    host = Host(bare)

    async def steps(client):
        first = await host.save(client, listing=host.listing())
        await host.save(
            client,
            fits=settle(first, {README: (CODEBASE, "readme"), QUOTE: None}),
        )
        bare.write(GUIDE, "# Guide\n")
        readme = await host.call(client, "kb_fit", fit_call(host, README))
        later = await host.save(client, listing=host.listing())
        return first, readme, later

    first, readme, later = session(server_parameters(tmp_path / "state"), steps)

    assert first["scopes"][0]["universe_specs"]
    assert set(entries(bare)) == {README, QUOTE}
    # The host sends the record-only `.knowledge-bus/` scope; bundled definitions still apply.
    assert host.universe_specs() == [{"folder": "", "files": []}]
    answer = checked(readme, "fit")
    assert (
        answer["candidates"][0]["universe_spec"],
        answer["candidates"][0]["kind"],
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
    host = Host(bare)

    async def steps(client):
        first = await host.save(client, listing=host.listing())
        await host.save(
            client,
            fits=settle(
                first,
                {
                    README: (CODEBASE, "readme"),
                    QUOTE: None,
                    NESTED_RFC: (PRODUCT, "design-doc"),
                },
            ),
        )
        bare.write(NESTED_NEW, "# Queue\n")
        nested = await host.call(client, "kb_fit", fit_call(host, NESTED_NEW))
        later = await host.save(client, listing=host.listing())
        return nested, later

    nested, later = session(server_parameters(tmp_path / "state"), steps)

    assert [item["folder"] for item in host.universe_specs()] == ["", "team"]
    answer = checked(nested, "fit")
    assert [(c["universe_spec"], c["kind"]) for c in answer["candidates"]] == [
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
