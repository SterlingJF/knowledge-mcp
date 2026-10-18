from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from knowledge_mcp import bundled
from tests.harness import (
    CODEBASE,
    PRODUCT,
    candidates,
    fit,
    knowledge_base,
    listed,
    scope_arguments,
    server_parameters,
    session,
    texts,
    type_arguments,
    write,
)

RFC = "docs/rfcs/0042-cache.md"
PRICING = "docs/product/pricing.md"
DOCS_PRICING = "docs/pricing.md"
ADR = "docs/adr/0001-use-dolt.md"
DRIVE = "https://drive.google.com/drive/folders/1AbCdEfGhIjK/0042-cache.md"


@pytest.fixture
def codebase(tmp_path: Path) -> Path:
    root = knowledge_base(tmp_path / "codebase", {"": [CODEBASE, PRODUCT]})
    write(root, RFC, "# Cache\n")
    write(root, PRICING, "# Pricing\n")
    write(root, DOCS_PRICING, "# Pricing\n")
    write(root, ADR, "# Use Dolt\n")
    return root


def ask(state: Path, *calls: tuple[str, dict]) -> list:
    async def steps(client):
        return [await client.call_tool(name, arguments) for name, arguments in calls]

    return session(server_parameters(state), steps)


class TestCodebase:
    def test_a_maintainer_gets_the_design_proposal_first(self, codebase, tmp_path):
        [result] = ask(
            tmp_path,
            ("kb_get_document_type", type_arguments(codebase, RFC, role="maintainer")),
        )
        answer = fit(result)

        assert candidates(answer)[0] == (CODEBASE, "design-proposal")
        first = answer["candidates"][0]
        assert first["actor"] == "the maintainers who decide on designs"
        assert first["role_matches"] is True

    def test_without_a_role_the_list_holds_both_design_documents(
        self, codebase, tmp_path
    ):
        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(codebase, RFC))
        )
        answer = fit(result)

        assert {(CODEBASE, "design-proposal"), (PRODUCT, "design-doc")} <= set(
            candidates(answer)
        )
        assert all("role_matches" not in item for item in answer["candidates"])

    def test_folder_match_includes_document_type_list(self, codebase, tmp_path):
        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(codebase, RFC))
        )
        answer = fit(result)

        assert {item["matched_on"] for item in answer["candidates"]} == {"folder"}
        assert (PRODUCT, "design-doc") in listed(answer)

    def test_unmatched_docs_file_returns_document_type_list(self, codebase, tmp_path):
        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(codebase, DOCS_PRICING))
        )
        answer = fit(result)

        assert answer["candidates"] == []
        assert (PRODUCT, "design-doc") in listed(answer)

    def test_adr_folder_matches_decision_record_only(self, codebase, tmp_path):
        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(codebase, ADR))
        )
        answer = fit(result)

        assert candidates(answer) == [(PRODUCT, "decision-record")]
        assert answer["candidates"][0]["matched"] == ["adr"]
        assert (CODEBASE, "contributing-guide") in listed(answer)

    def test_unmatched_file_lists_design_types_and_supports_card_lookup(
        self, codebase, tmp_path
    ):
        arguments = type_arguments(codebase, PRICING, role="product lead")
        card = {**scope_arguments(codebase, PRICING), "location": arguments["location"]}
        fitted, carded = ask(
            tmp_path,
            ("kb_get_document_type", arguments),
            ("kbp_card", {**card, "kind": "design-doc", "universe": PRODUCT}),
        )
        answer = fit(fitted)

        assert answer["candidates"] == []
        assert (PRODUCT, "design-doc") in listed(answer)
        assert (CODEBASE, "design-proposal") in listed(answer)
        assert not carded.is_error, texts(carded)
        markdown = texts(carded)[0]
        assert markdown.startswith("# Design doc\n")
        assert "Product development universe spec (product-development" in markdown
        assert "Depends on:" in markdown

    def test_bundled_copies_are_labelled_with_the_ref(self, codebase, tmp_path):
        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(codebase, RFC))
        )
        answer = fit(result)

        label = f"bundled copy at {bundled.ref()}"
        assert {spec["id"]: spec["source"] for spec in answer["universe_specs"]} == {
            CODEBASE: label,
            PRODUCT: label,
        }

    def test_sent_definitions_return_source_labels_and_digests(
        self, codebase, tmp_path
    ):
        [result] = ask(
            tmp_path,
            ("kb_get_document_type", type_arguments(codebase, RFC, send_text=True)),
        )
        answer = fit(result)

        assert {spec["source"] for spec in answer["universe_specs"]} == {
            "sent by the harness"
        }
        assert {item["name"] for item in answer["received"]} == {
            f"{CODEBASE}.kbp.yaml",
            f"{CODEBASE}.type-guidance.kbp.yaml",
            f"{PRODUCT}.kbp.yaml",
            f"{PRODUCT}.type-guidance.kbp.yaml",
        }
        assert all(item["digest"].startswith("sha256:") for item in answer["received"])


def test_single_universe_returns_kinds_and_matching_fit(tmp_path):
    root = knowledge_base(tmp_path / "notes", {"": [PRODUCT]})
    write(root, PRICING)
    scope = {**scope_arguments(root, PRICING), "location": str(root / PRICING)}

    kinds, fitted = ask(
        tmp_path,
        ("kbp_kinds", scope),
        ("kb_get_document_type", type_arguments(root, "docs/rfcs/0042-cache.md")),
    )

    assert not kinds.is_error, texts(kinds)
    assert json.loads(texts(kinds)[0])["schema"] == "knowledge-bus/kinds/1"
    assert candidates(fit(fitted)) == [(PRODUCT, "design-doc")]


class TestNoKnowledgeBusFolder:
    def test_a_readme_fits_the_bundled_readme(self, tmp_path):
        root = tmp_path / "plain"
        write(root, "README.md", "# Plain\n")

        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(root, "README.md"))
        )
        answer = fit(result)

        assert candidates(answer)[0] == (CODEBASE, "readme")
        assert {spec["id"] for spec in answer["universe_specs"]} == {CODEBASE, PRODUCT}
        assert {spec["source"] for spec in answer["universe_specs"]} == {
            f"bundled copy at {bundled.ref()}"
        }

    def test_unmatched_vendor_quote_returns_type_list_without_candidates(
        self, tmp_path
    ):
        root = tmp_path / "plain"
        write(root, "vendor-quote.md", "Quote\n")

        [result] = ask(
            tmp_path, ("kb_get_document_type", type_arguments(root, "vendor-quote.md"))
        )
        answer = fit(result)

        assert answer["candidates"] == []
        assert {group["universe_spec"] for group in answer["every_document_type"]} == {
            CODEBASE,
            PRODUCT,
        }
        assert (CODEBASE, "readme") in listed(answer)


def test_from_parent_preserves_card_content_except_presentation(tmp_path):
    root = knowledge_base(tmp_path / "company", {"": [CODEBASE, PRODUCT], "team": []})
    write(root, "team/.knowledge-bus/workspace.yaml", f"from_parent:\n  - {PRODUCT}\n")
    nested = "team/rfcs/0042-cache.md"
    parent = "rfcs/0042-cache.md"

    def card(document):
        return (
            "kbp_card",
            {
                **scope_arguments(root, document),
                "location": str(root / document),
                "kind": "design-doc",
                "universe": PRODUCT,
            },
        )

    fitted, nested_card, parent_card = ask(
        tmp_path,
        ("kb_get_document_type", type_arguments(root, nested)),
        card(nested),
        card(parent),
    )
    answer = fit(fitted)

    assert candidates(answer) == [(PRODUCT, "design-doc")]
    assert [(s["id"], s["from_parent"]) for s in answer["universe_specs"]] == [
        (PRODUCT, True)
    ]
    nested_text, parent_text = (
        without_presentation(texts(r)[0]) for r in (nested_card, parent_card)
    )
    assert nested_text == parent_text


def without_presentation(card: str) -> str:
    """Exclude presentation details because kbp derives them from the universe specs available in each folder."""
    head, _, rest = card.partition("\n## How to present it\n")
    _, conditions, tail = rest.partition("\n## What the conditions mean\n")
    return head + conditions + tail


class TestAnySource:
    def test_drive_location_preserves_other_fit_response_fields(
        self, codebase, tmp_path
    ):
        local = type_arguments(codebase, RFC)
        drive = type_arguments(codebase, RFC, location=DRIVE)
        assert not Path(DRIVE).exists()

        here, there = ask(
            tmp_path, ("kb_get_document_type", local), ("kb_get_document_type", drive)
        )

        left, right = fit(here), fit(there)
        assert right.pop("location") == DRIVE
        left.pop("location")
        assert left == right

    def test_fit_response_is_unchanged_for_inaccessible_source_folder(
        self, codebase, tmp_path
    ):
        arguments = [
            ("kb_get_document_type", type_arguments(codebase, RFC, send_text=True)),
            ("kb_get_document_type", type_arguments(codebase, PRICING)),
        ]
        open_answers = [fit(result) for result in ask(tmp_path / "open", *arguments)]
        os.chmod(codebase, 0)
        try:
            closed_answers = [
                fit(result) for result in ask(tmp_path / "closed", *arguments)
            ]
        finally:
            os.chmod(codebase, 0o755)

        assert closed_answers == open_answers


def test_bundled_headers_reduce_first_call_argument_size(codebase, tmp_path):
    full = json.dumps(type_arguments(codebase, RFC, send_text=True))
    headers = json.dumps(type_arguments(codebase, RFC))
    [result] = ask(tmp_path, ("kb_get_document_type", type_arguments(codebase, RFC)))
    assert texts(result)
    assert len(headers) * 20 < len(full)
