from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from knowledge_mcp import document_types as records
from knowledge_mcp import local_type
from knowledge_mcp.cli import kb
from tests.kb_cli import run_kb
from tests.test_convention_filing_end_to_end import values
from tests.test_conventions_end_to_end import PLACE, stored, upsert
from tests.test_filing_end_to_end import SUBJECT, typed
from tests.test_kb_output_end_to_end import output_pty


def vault(tmp_path):
    root = tmp_path / "vault"
    document = root / SUBJECT
    document.parent.mkdir(parents=True)
    document.write_text("# Content")
    config = root / PLACE
    config.parent.mkdir(parents=True)
    config.write_text(stored())
    (root / records.PLACE).write_text(records.dump({SUBJECT: typed()}))
    return root


def test_c01_c02_c03_c05_c06_output_parity_read_boundary_and_no_writes(tmp_path):
    root = vault(tmp_path)
    args = [
        "type",
        str(root / SUBJECT),
        "--root",
        str(root),
        "--filing-values",
        json.dumps([values()]),
    ]
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    original = type(root).read_text

    def guarded(path, *args, **kwargs):
        assert path != root / SUBJECT
        return original(path, *args, **kwargs)

    with patch("pathlib.Path.read_text", guarded):
        result = CliRunner().invoke(kb, args)
        assert result.exit_code == 0, result.output
        assert "\tDecisions\tUse a Shared Cache.md\t" in result.output
        data = CliRunner().invoke(kb, [*args, "--json"])
        text, failed = local_type.document_type(
            root / SUBJECT, root=root, filing_values=[values()]
        )
        assert not failed
        assert json.loads(data.stdout) == json.loads(text)
    assert {p: p.read_bytes() for p in before} == before


def test_c04_missing_values(tmp_path):
    root = vault(tmp_path)
    args = ["type", str(root / SUBJECT), "--root", str(root)]
    result = CliRunner().invoke(kb, args)
    assert result.exit_code == 0
    assert "\t<none>\t<none>\t" in result.stdout
    assert "Naming needs document title" in result.stderr
    data = CliRunner().invoke(kb, [*args, "--json"])
    assert data.exit_code == 0
    assert "Naming needs" not in data.stderr
    assert json.loads(data.stdout)["filing"][0]["needed"]


@pytest.mark.parametrize("text", ["[", "{}", "[1]"])
def test_c07_invalid_json(tmp_path, text):
    root = vault(tmp_path)
    result = run_kb(
        tmp_path,
        "type",
        str(root / SUBJECT),
        "--root",
        str(root),
        "--filing-values",
        text,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Correct the JSON array" in result.stderr
    assert "kb type --help" in result.stderr
    assert "kb doctor" not in result.stderr


def test_c08_invalid_supplied_value(tmp_path):
    root = vault(tmp_path)
    change = upsert()
    change["name"]["parts"].append(
        {"part": "date", "property": "decision_date", "format": "YYYY"}
    )
    (root / PLACE).write_text(stored(change))
    item = values()
    item["properties"]["decision_date"] = "2026-02-29"
    result = run_kb(
        tmp_path,
        "type",
        str(root / SUBJECT),
        "--root",
        str(root),
        "--json",
        "--filing-values",
        json.dumps([item]),
    )
    assert result.returncode == 1
    assert "Correct the naming values" in result.stderr
    assert "--filing-values" in result.stderr.splitlines()[-2]
    assert "kb type --help" in result.stderr.splitlines()[-2]
    assert "kb doctor" not in result.stderr
    assert json.loads(result.stderr.splitlines()[-1])["errors"][0][
        "pointer"
    ].startswith("#/filing_values")


def test_c09_invalid_configuration(tmp_path):
    root = vault(tmp_path)
    (root / PLACE).write_text("[")
    result = run_kb(tmp_path, "type", str(root / SUBJECT), "--root", str(root))
    assert result.returncode == 1
    assert "conventions.yaml" in result.stderr


def test_c10_help_and_flags():
    runner = CliRunner()
    for flag in ["-h", "--help"]:
        result = runner.invoke(kb, ["type", flag])
        assert result.exit_code == 0
        assert "--filing-values" in result.output
    for flag in ["--filing-values", "--filing-value", "--filing-vlaues"]:
        assert runner.invoke(kb, ["type", "note.md", flag]).exit_code == 2


def test_c01_terminal_seven_columns(tmp_path):
    root = vault(tmp_path)
    args = [
        "type",
        str(root / SUBJECT),
        "--root",
        str(root),
        "--filing-values",
        json.dumps([values()]),
    ]
    code, terminal, stderr = output_pty(tmp_path, args)
    assert code == 0, stderr
    assert terminal.splitlines()[0].split() == [
        "TYPE",
        "SPEC",
        "MATCHED-BY",
        "USED-BY",
        "PROPOSED-FOLDER",
        "PROPOSED-NAME",
        "TITLE",
    ]
    assert "Use a Shared Cache.md" in terminal


def test_filing_help_has_complete_json_example():
    result = CliRunner().invoke(kb, ["type", "--help"])
    assert result.exit_code == 0
    assert "--filing-values" in result.stdout
    compact = "".join(result.stdout.split())
    for field in [
        '"path":',
        '"universe_spec":',
        '"document_type":',
        '"properties":{"project":"Atlas"}',
        '"content":"Useasharedcache"',
    ]:
        assert field in compact
