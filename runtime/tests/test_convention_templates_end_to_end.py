from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

import anyio
import pytest
import yaml

from knowledge_mcp import convention_templates, conventions, schemas
from knowledge_mcp.main import build_server
from tests.harness import checked, server_parameters, session, validator


def catalog():
    return checked(
        anyio.run(
            build_server().call_tool,
            "kb_list_convention_templates",
            {"location": "unreachable://vault"},
        ),
        "convention-templates",
    )


def variant(template, name):
    return deepcopy(
        next(
            v
            for t in catalog()["templates"]
            if t["id"] == template
            for v in t["variants"]
            if v["id"] == name
        )
    )


def test_t01_t03_catalog_stdio_and_stable_sessions(tmp_path):
    async def steps(client):
        return checked(
            await client.call_tool(
                "kb_list_convention_templates", {"location": "unreachable://vault"}
            ),
            "convention-templates",
        )

    first = session(server_parameters(tmp_path / "first"), steps)
    second = session(server_parameters(tmp_path / "second"), steps)
    assert first == second == catalog()
    assert [t["id"] for t in first["templates"]] == ["ace", "para", "johnny-decimal"]
    assert [len(t["variants"]) for t in first["templates"]] == [4, 4, 1]


def test_t02_catalog_opens_no_location_or_network():
    with (
        patch("socket.create_connection", side_effect=AssertionError("network")),
        patch("pathlib.Path.iterdir", side_effect=AssertionError("vault inventory")),
    ):
        assert catalog()["location"] == "unreachable://vault"


def test_t14_sources_and_complete_patterns():
    for template in catalog()["templates"]:
        sources = {s["url"] for s in template["sources"]}
        assert len(sources) == len(template["sources"])
        assert len({v["id"] for v in template["variants"]}) == len(template["variants"])
        for item in template["variants"]:
            assert set(item["folder_sources"] + item["name_sources"]) <= sources
            assert item["adaptation"]
            conventions.validate_pattern({**item, "folder": item["folder"] or []}, "#")
    daily = variant("ace", "calendar-daily")
    assert daily["name"]["parts"] == [
        {"part": "date", "property": "date", "format": "YYYY-MM-DD"}
    ]
    assert "content" not in daily
    assert variant("ace", "atlas-title")["name_sources"] == []
    assert "knowledge-mcp" in variant("para", "projects-title")["adaptation"]
    assert variant("johnny-decimal", "id-date-title")["folder"] is None


@pytest.mark.parametrize(
    "mutation", ["unknown", "missing-name", "bad-part", "bad-folder"]
)
def test_catalog_contract_rejects_malformed_variants(mutation):
    answer = catalog()
    item = answer["templates"][0]["variants"][0]
    if mutation == "unknown":
        item["extra"] = True
    elif mutation == "missing-name":
        item.pop("name")
    elif mutation == "bad-part":
        item["name"]["parts"] = [{"part": "guess"}]
    else:
        item["folder"] = ["../Atlas"]
    assert list(validator("convention-templates").iter_errors(answer))


@pytest.mark.parametrize("mutation", ["template-id", "variant-id", "source", "content"])
def test_catalog_resource_validation_rejects_incomplete_definitions(tmp_path, mutation):
    schemas.bundle("problem")
    data = catalog()
    data.pop("schema")
    data.pop("location")
    if mutation == "template-id":
        data["templates"][1]["id"] = "ace"
    elif mutation == "variant-id":
        data["templates"][0]["variants"][1]["id"] = "atlas-title"
    elif mutation == "source":
        data["templates"][0]["variants"][0]["name_sources"] = [
            "https://unlisted.invalid"
        ]
    else:
        data["templates"][0]["variants"][0].pop("content")
    (tmp_path / "convention_templates.yaml").write_text(yaml.safe_dump(data))
    with patch.object(convention_templates.resources, "files", return_value=tmp_path):
        result = anyio.run(
            build_server().call_tool,
            "kb_list_convention_templates",
            {"location": "vault"},
        )
    assert result.is_error
    assert result.structured_content["type"].endswith("/internal-error")


def test_catalog_uses_existing_argument_problem():
    result = anyio.run(
        build_server().call_tool,
        "kb_list_convention_templates",
        {"location": "vault", "template": "ace"},
    )
    assert result.is_error
    assert result.structured_content["type"].endswith("/argument-invalid")
