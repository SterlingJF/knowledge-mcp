from __future__ import annotations

import json

from knowledge_mcp import local_type
from tests.harness import PRODUCT
from tests.test_conventions_end_to_end import PLACE
from tests.test_team_conventions_end_to_end import config, entry


def test_c10_type_uses_nested_conventions(tmp_path):
    target = tmp_path / "Finance/decision-record.md"
    target.parent.mkdir()
    target.write_text("# Unread content")
    config_file = tmp_path / "Finance" / PLACE
    config_file.parent.mkdir(parents=True)
    config_file.write_text(config(entry(PRODUCT, "decision-record", "Decisions")))
    text, failed = local_type.document_type(
        target,
        root=tmp_path,
        filing_values=[
            dict(
                path="Finance/decision-record.md",
                universe_spec=PRODUCT,
                document_type="decision-record",
                properties={},
                content="Approved",
            )
        ],
    )
    assert not failed
    assessment = next(
        e for e in json.loads(text)["filing"] if e["document_type"] == "decision-record"
    )
    assert assessment["proposal"]["path"] == "Finance/Decisions/Approved.md"
    assert assessment["convention"]["folder"] == "Finance"
