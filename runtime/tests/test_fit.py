"""knowledge-mcp's own matching of a file name and folder against the document types in scope."""

from __future__ import annotations

from knowledge_mcp.fit import answer, words

LISTING = {
    "schema": "knowledge-bus/kinds-set/1",
    "from_parent": [],
    "universe_specs": [
        {
            "schema": "knowledge-bus/kinds/1",
            "universe_spec": {
                "id": "codebase-recordkeeping",
                "label": "Codebase recordkeeping",
                "version": "0.1",
                "covers": "The written documents of a codebase: files in its repository.",
                "for": "Anyone who uses a software project.",
            },
            "kinds": [
                {
                    "kind": "readme",
                    "name": "Readme",
                    "alias": {
                        "kind": "descriptive",
                        "form": "README file at the repository root",
                    },
                    "action": "decide whether to try the project",
                    "actor": "a first-time visitor",
                    "timing": "on the first visit",
                },
                {
                    "kind": "design-proposal",
                    "name": "Design proposal",
                    "alias": {
                        "kind": "descriptive",
                        "form": "RFC, enhancement proposal",
                    },
                    "action": "accept or reject a proposed design",
                    "actor": "the maintainers who decide on designs",
                    "timing": "before anyone builds the design",
                },
            ],
            "factors": [],
        },
        {
            "schema": "knowledge-bus/kinds/1",
            "universe_spec": {
                "id": "product-development",
                "label": "Product development",
                "version": "0.9",
                "covers": "The reasoning around deliberate work.",
                "for": "Whoever is accountable.",
            },
            "kinds": [
                {
                    "kind": "opportunity-assessment",
                    "name": "Opportunity assessment",
                    "alias": {
                        "kind": "descriptive",
                        "form": "product brief / one-pager",
                    },
                    "action": "decide whether to fund the work",
                    "actor": "whoever would fund the work",
                    "timing": None,
                },
                {
                    "kind": "design-doc",
                    "name": "Design doc",
                    "alias": {"kind": "descriptive", "form": "RFC / RFD"},
                    "action": "review a design",
                    "actor": "reviewer",
                    "timing": None,
                },
                {
                    "kind": "lean-canvas",
                    "name": "Lean canvas",
                    "alias": None,
                    "action": "test a venture",
                    "actor": "whoever is starting the venture",
                    "timing": None,
                },
            ],
            "factors": [],
        },
    ],
}

SPECS = [
    {
        "id": "codebase-recordkeeping",
        "version": "0.1",
        "source": "sent by the host",
        "from_parent": False,
    },
    {
        "id": "product-development",
        "version": "0.9",
        "source": "sent by the host",
        "from_parent": False,
    },
]


def fitted(name, folders, hat=None):
    return answer(
        LISTING,
        location=name,
        name=name,
        folders=folders,
        hat=hat,
        universe_specs=SPECS,
    )


def pairs(result):
    return [(item["universe_spec"], item["kind"]) for item in result["candidates"]]


def test_words_split_case_separators_and_plurals():
    assert words("0042-cache.md") == {"cache", "md"}
    assert words("ReleaseNotes") == {"release", "note"}
    assert words("rfcs") == {"rfc"}
    assert words("CODEOWNERS") == {"codeowner"}
    assert words("categories") == {"category"}
    assert words("process") == {"process"}


def test_filename_and_containing_folder_match_document_types():
    assert pairs(fitted("0042-cache.md", ["docs", "rfcs"])) == [
        ("codebase-recordkeeping", "design-proposal"),
        ("product-development", "design-doc"),
    ]
    assert pairs(fitted("README.md", [])) == [("codebase-recordkeeping", "readme")]


def test_matching_ignores_aliases_in_farther_folders():
    result = fitted("notes.md", ["rfcs", "misc"])
    assert result["candidates"] == []


def test_universe_word_ranks_universes_without_type_candidates():
    result = fitted("pricing.md", ["docs", "product"])
    assert result["candidates"] == []
    assert [group["universe_spec"] for group in result["every_document_type"]] == [
        "product-development",
        "codebase-recordkeeping",
    ]
    assert result["every_document_type"][0]["covers_matched"] == ["product"]


def test_the_hat_puts_matching_actors_first():
    result = fitted("0042-cache.md", ["rfcs"], hat="reviewer")
    assert pairs(result)[0] == ("product-development", "design-doc")
    assert [item["hat_matches"] for item in result["candidates"]] == [True, False]


def test_filename_match_omits_document_type_list():
    assert fitted("README.md", [])["every_document_type"] is None
    folder_only = fitted("0042-cache.md", ["rfcs"])
    assert {item["matched_on"] for item in folder_only["candidates"]} == {"folder"}
    assert folder_only["every_document_type"] is not None
    listing = fitted("vendor-quote.md", [])["every_document_type"]
    assert [kind["kind"] for group in listing for kind in group["kinds"]] == [
        "readme",
        "design-proposal",
        "opportunity-assessment",
        "design-doc",
        "lean-canvas",
    ]
    assert set(listing[0]["kinds"][0]) == {"kind", "action", "actor"}


def test_candidates_carry_their_kinds_fields():
    [first, _] = fitted("0042-cache.md", ["rfcs"])["candidates"]
    assert first == {
        "universe_spec": "codebase-recordkeeping",
        "kind": "design-proposal",
        "name": "Design proposal",
        "alias": {"kind": "descriptive", "form": "RFC, enhancement proposal"},
        "action": "accept or reject a proposed design",
        "actor": "the maintainers who decide on designs",
        "timing": "before anyone builds the design",
        "matched": ["rfc"],
        "matched_on": "folder",
    }


def test_single_universe_listing_returns_matching_type():
    single = LISTING["universe_specs"][1]
    result = answer(
        single,
        location="x",
        name="0042-cache.md",
        folders=["rfcs"],
        hat=None,
        universe_specs=SPECS[1:],
    )
    assert pairs(result) == [("product-development", "design-doc")]
