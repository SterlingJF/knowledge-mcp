from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from knowledge_mcp import document_types as records
from knowledge_mcp import local_type
from knowledge_mcp.cli import kb
from tests.test_filing_end_to_end import SUBJECT, typed


def test_c01_c02_c03_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MCP_STATE_DIR", str(tmp_path / "state"))
    root = tmp_path / "vault"
    paths = [SUBJECT, "decisions/cache-policy.md", "decisions/queue-policy.md"]
    for path in paths:
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# Content\n")
    saved = root / records.PLACE
    saved.parent.mkdir(parents=True)
    saved.write_text(records.dump({p: typed() for p in paths}))
    before = {p: (root / p).read_bytes() for p in [*paths, records.PLACE]}
    original = type(saved).read_text

    def guarded(path, *args, **kwargs):
        assert path not in [root / p for p in paths]
        return original(path, *args, **kwargs)

    with patch("pathlib.Path.read_text", guarded):
        text, failed = local_type.document_type(root / SUBJECT, root=root)
        assert not failed
    assert (
        json.loads(text)["filing"][0]["proposal"]["path"] == "decisions/cache-plan.md"
    )
    result = CliRunner().invoke(kb, ["type", str(root / SUBJECT), "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert "\tdecisions\tcache-plan.md\t" in result.output
    assert {p: (root / p).read_bytes() for p in before} == before


def test_c04_help_and_errors():
    runner = CliRunner()
    result = runner.invoke(kb, ["type", "--help"])
    assert result.exit_code == 0
    assert "PROPOSED-FOLDER PROPOSED-NAME" in result.output
    assert runner.invoke(kb, ["type"]).exit_code == 2
