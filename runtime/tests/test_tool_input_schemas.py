from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from tests.harness import server_parameters, session
from tests.test_proposal_end_to_end import DEMO, NEW, REVISED

# The proposal schema was 6577 bytes with `$defs`; inlined it is 5734.
PROPOSAL_LIMIT = 6600


def listed_inputs(tmp_path):
    async def steps(client):
        return (await client.list_tools()).tools

    return {
        tool.name: tool.input_schema
        for tool in session(server_parameters(tmp_path), steps)
    }


def keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from keys(item)


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    return listed_inputs(tmp_path_factory.mktemp("listed"))


def test_every_listed_input_schema_is_inlined(inputs):
    assert len(inputs) == 20
    for name, schema in inputs.items():
        found = set(keys(schema)) & {"$ref", "$defs"}
        assert not found, f"{name} publishes {found}"


def test_inlined_proposal_schema_accepts_the_samples(inputs):
    validator = Draft202012Validator(inputs["kb_prepare_proposal"])
    for sample in (DEMO, NEW, REVISED):
        assert not list(validator.iter_errors(sample))


def test_inlined_proposal_schema_refuses_invented_row_fields(inputs):
    validator = Draft202012Validator(inputs["kb_prepare_proposal"])
    row = {"change": "Evening build retirement", "evidence": "supported"}
    row["sources"] = [{"file": "meeting-notes.md", "line_number": 15}]
    assert list(validator.iter_errors({**DEMO, "rows": [row]}))


def test_optional_fields_are_plain_properties(inputs):
    row = inputs["kb_prepare_proposal"]["properties"]["rows"]["items"]
    mark = row["properties"]["mark"]
    assert "anyOf" not in mark
    assert "default" not in mark
    assert mark["enum"] == ["supported", "partly", "conflicting", "suggested"]
    assert mark["description"]
    assert row["properties"]["current"]["description"]
    for source in row["properties"]["sources"]["items"]["anyOf"]:
        assert source["description"]


def test_proposal_schema_stays_small(inputs):
    size = len(json.dumps(inputs["kb_prepare_proposal"], separators=(",", ":")))
    assert size <= PROPOSAL_LIMIT
