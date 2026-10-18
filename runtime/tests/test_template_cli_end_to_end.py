from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from knowledge_mcp import document_types as records
from knowledge_mcp.cli import kb
from tests.kb_cli import run_kb
from tests.test_conventions_end_to_end import PLACE
from tests.test_kb_output_end_to_end import output_pty
from tests.test_template_workflow_end_to_end import (
    SPEC,
    lookup,
    note_spec,
    proposal,
    stored,
    typed,
)


@pytest.mark.parametrize(
    "experience",
    [
        (
            "ace",
            "calendar-daily",
            "daily-note",
            None,
            {"date": "2026-10-18"},
            None,
            "Calendar/2026-10-18.md",
        ),
        (
            "ace",
            "atlas-title",
            "knowledge-note",
            ["Atlas (general notes)"],
            {},
            "Memory",
            "Atlas (general notes)/Memory.md",
        ),
        (
            "para",
            "projects-title",
            "project-note",
            ["Projects", {"part": "property", "property": "project"}],
            {"project": "Garden redesign"},
            "Supplier shortlist",
            "Projects/Garden redesign/Supplier shortlist.md",
        ),
        (
            "johnny-decimal",
            "id-date-title",
            "meeting-note",
            ["10-19 Work", "12 Meetings", "12.03 Product reviews"],
            {"date": "2026-10-18"},
            "Launch discussion",
            "10-19 Work/12 Meetings/12.03 Product reviews/2026-10-18 Launch discussion.md",
        ),
    ],
)
def test_c01_c04_c05_c07_subprocess_templates_and_no_writes(tmp_path, experience):
    template, name, kind, folder, properties, content, expected = experience
    change = proposal(template, name, kind, folder)
    root, args, _values = cli_vault(tmp_path, change, properties, content)
    before = {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    result = run_kb(tmp_path, *args, "--json")
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout)
    assert answer["filing"][0]["proposal"]["path"] == expected
    assert (
        answer["filing"]
        == lookup(
            change,
            properties=properties,
            content=content,
            config=(root / PLACE).read_text(),
        )["filing"]
    )
    pipe = run_kb(tmp_path, *args)
    assert pipe.returncode == 0
    assert len(pipe.stdout.strip().split("\t")) == 7
    original = type(root).read_text

    def guarded(path, *a, **kw):
        assert path != root / "Inbox/Sunday.md"
        return original(path, *a, **kw)

    with patch("pathlib.Path.read_text", guarded):
        assert CliRunner().invoke(kb, args).exit_code == 0
    assert {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    } == before


def cli_vault(tmp_path, change, properties, content):
    root = tmp_path / "vault"
    path = "Inbox/Sunday.md"
    config = root / PLACE
    config.parent.mkdir(parents=True)
    (root / ".knowledge-bus/personal-notes.kbp.yaml").write_text(note_spec())
    (root / path).parent.mkdir()
    (root / path).write_text("# Private note\n")
    config.write_text(stored(change))
    (config.parent / "document-types.yaml").write_text(
        records.dump({path: typed(change["document_type"])})
    )
    values = {
        "path": path,
        "universe_spec": SPEC,
        "document_type": change["document_type"],
        "properties": properties,
    }
    if content is not None:
        values["content"] = content
    args = [
        "type",
        str(root / path),
        "--root",
        str(root),
        "--filing-values",
        json.dumps([values]),
    ]
    return root, args, values


@pytest.mark.parametrize(("value", "code"), [(None, 0), ("2026-02-29", 1), ("[", 2)])
def test_c06_missing_invalid_date_and_json(tmp_path, value, code):
    root, args, values = cli_vault(tmp_path, proposal(), {}, None)
    if value == "[":
        args[-1] = value
    elif value is not None:
        values["properties"]["date"] = value
        args[-1] = json.dumps([values])
    result = run_kb(tmp_path, *args, "--json")
    assert result.returncode == code, result.stderr
    if value is None:
        assert json.loads(result.stdout)["filing"][0]["status"] == "values_needed"
    assert (root / "Inbox/Sunday.md").read_text() == "# Private note\n"


def test_c05_terminal_preserves_seven_columns(tmp_path):
    _root, args, _values = cli_vault(tmp_path, proposal(), {"date": "2026-10-18"}, None)
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
    assert "2026-10-18.md" in terminal
