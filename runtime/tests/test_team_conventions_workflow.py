from __future__ import annotations

from pathlib import Path

import yaml

from knowledge_mcp.main import build_server
from tests.harness import PRODUCT
from tests.test_conventions_end_to_end import PERMISSION
from tests.test_team_conventions_end_to_end import (
    FINANCE,
    INVOICE,
    config,
    entry,
    inspect,
    prepare,
    spec,
)

ROOT = Path(__file__).resolve().parents[2]
WRITE_SKILL = ROOT / "runtime/skills/kb-write-document/SKILL.md"


def test_local_definition_workflow_preserves_bundled_id_and_version():
    skill = WRITE_SKILL.read_text()
    assert 'First try the actual file SHA-256 as `digest: "sha256:…"`' in skill
    assert "if unknown, send exact full `text`" in skill
    assert "while the text is unchanged" in skill
    assert "Include `text` when those values match no file bundled" not in skill
    for name in ("kb-track-document-types", "kb-import-document"):
        assert (
            "`kb-write-document`"
            in (ROOT / "runtime/skills" / name / "SKILL.md").read_text()
        )

    server = build_server()
    definitions = [
        spec("", PRODUCT),
        spec("Finance", PRODUCT, [("Product development", "Team operations")]),
    ]
    conventions = [
        dict(folder="", text=config(entry(PRODUCT, "decision-record", "Decisions"))),
        dict(folder="Finance", text=""),
    ]
    answer = inspect(
        server=server,
        knowledge_bus_folders=definitions,
        conventions_files=conventions,
    )
    assert answer["conventions"] == []
    assert answer["inactive"][0]["reason"] == "definition_differs"
    for definition, received in zip(definitions, answer["received"], strict=False):
        definition["files"][0].pop("text")
        definition["files"][0]["digest"] = received["digest"]
    reused = inspect(
        server=server,
        knowledge_bus_folders=definitions,
        conventions_files=conventions,
    )
    assert reused["inactive"] == answer["inactive"]
    assert reused["conventions"] == []


def test_last_local_removal_keeps_valid_yaml_and_parent_selections():
    skill = WRITE_SKILL.read_text()
    assert "Keep valid conventions YAML with `conventions: []`" in skill
    assert "Preserve accepted `from_parent` selections and the saved boundary." in skill
    assert "Keep an empty conventions file" not in skill
    answer = prepare(
        conventions=FINANCE,
        changes=[
            dict(change="remove", universe_spec=INVOICE[0], document_type=INVOICE[1])
        ],
        allowed_by=PERMISSION,
    )
    assert answer["status"] == "ready"
    saved = yaml.safe_load(answer["record"])
    assert saved["conventions"] == []
    assert saved["from_parent"] == yaml.safe_load(FINANCE)["from_parent"]
