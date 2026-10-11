"""Test audience choices from each document type's universe spec through the stdio server."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from knowledge_mcp import bundled
from tests.hosts import (
    CODEBASE,
    PRODUCT,
    checked,
    knowledge_base,
    scope_arguments,
    server_parameters,
    session,
    texts,
    write,
)

RFC = "docs/rfcs/0042-cache.md"
PRICING = "docs/product/pricing.md"
AUDIENCE = ["self", "internal", "counterparty", "regulator", "public"]


@pytest.fixture
def codebase(tmp_path: Path) -> Path:
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC, "# Cache\n")
    write(root, PRICING, "# Pricing\n")
    return root


def ask(state: Path, *calls: tuple[str, dict]) -> list:
    async def steps(client):
        return [await client.call_tool(name, arguments) for name, arguments in calls]

    return session(server_parameters(state), steps)


def audience_arguments(root: Path, document: str, kind: str, **extra) -> dict:
    return {
        **scope_arguments(root, document, send_text=extra.pop("send_text", False)),
        "location": str(root / document),
        "kind": kind,
        **extra,
    }


def test_design_doc_returns_audience_frame_values(codebase, tmp_path):
    [result] = ask(
        tmp_path, ("kb_audience", audience_arguments(codebase, PRICING, "design-doc"))
    )
    answer = checked(result, "audience")

    assert answer["universe_spec"] == {
        "id": PRODUCT,
        "version": "0.9",
        "source": f"bundled copy at {bundled.ref()}",
    }
    assert answer["kind"] == "design-doc"
    assert answer["actor"] == "reviewer"
    assert answer["frame"] == {
        "id": "audience",
        "question": "Who is this artifact going to?",
    }
    assert [choice["id"] for choice in answer["choices"]] == AUDIENCE
    assert answer["choices"][0]["label"] == "Self"


def test_design_proposal_returns_actor_without_choices(codebase, tmp_path):
    [result] = ask(
        tmp_path,
        ("kb_audience", audience_arguments(codebase, RFC, "design-proposal")),
    )
    answer = checked(result, "audience")

    assert answer["universe_spec"]["id"] == CODEBASE
    assert answer["actor"] == "the maintainers who decide on designs"
    assert answer["frame"] is None
    assert answer["choices"] == []


def test_host_defined_audience_choices_are_reused_by_digest(codebase, tmp_path):
    universe = codebase / ".knowledge-bus" / f"{PRODUCT}.kbp.yaml"
    text = universe.read_text()
    assert "values: [self, internal, counterparty, regulator, public]" in text
    universe.write_text(
        text.replace(
            "values: [self, internal, counterparty, regulator, public]",
            "values: [self, partner]",
        )
    )
    first = audience_arguments(codebase, PRICING, "design-doc", send_text=True)

    async def steps(client):
        sent = checked(await client.call_tool("kb_audience", first), "audience")
        digests = {item["name"]: item["digest"] for item in sent["received"]}
        later = audience_arguments(codebase, PRICING, "design-doc")
        for scope in later["universe_specs"]:
            for spec in scope["files"]:
                spec["digest"] = digests[spec["name"]]
        return sent, checked(await client.call_tool("kb_audience", later), "audience")

    sent, later = session(server_parameters(tmp_path), steps)

    assert [choice["id"] for choice in sent["choices"]] == ["self", "partner"]
    assert sent["universe_spec"]["source"] == "sent by the host"
    assert later["choices"] == sent["choices"]
    assert later["received"] == []


def test_single_universe_spec_returns_audience_choices(tmp_path):
    root = knowledge_base(tmp_path / "notes", {"": [PRODUCT]})
    write(root, PRICING)

    [result] = ask(
        tmp_path, ("kb_audience", audience_arguments(root, PRICING, "design-doc"))
    )

    assert [c["id"] for c in checked(result, "audience")["choices"]] == AUDIENCE


def test_ambiguous_type_requires_universe_argument(codebase, tmp_path):
    arguments = audience_arguments(codebase, PRICING, "architecture-overview")
    unsettled, settled = ask(
        tmp_path,
        ("kb_audience", arguments),
        ("kb_audience", {**arguments, "universe": CODEBASE}),
    )

    assert unsettled.is_error
    [message] = texts(unsettled)
    assert CODEBASE in message and PRODUCT in message and "`universe`" in message
    assert checked(settled, "audience")["universe_spec"]["id"] == CODEBASE


def test_an_unknown_document_type_is_refused(codebase, tmp_path):
    [result] = ask(
        tmp_path, ("kb_audience", audience_arguments(codebase, PRICING, "not-a-type"))
    )

    assert result.is_error
    assert "not-a-type" in texts(result)[0]


def test_each_answer_is_logged_once(codebase, tmp_path):
    calls = [
        ("kb_audience", audience_arguments(codebase, PRICING, "design-doc")),
        ("kb_audience", audience_arguments(codebase, RFC, "design-proposal")),
    ]
    results = ask(tmp_path, *calls)

    log = tmp_path / "knowledge-mcp" / "log.jsonl"
    logged = [json.loads(line) for line in log.read_text().splitlines()]
    assert [entry["tool"] for entry in logged] == ["kb_audience", "kb_audience"]
    assert [entry["returned"] for entry in logged] == [texts(r) for r in results]
