from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/mcp-tools.mdx"
GENERATOR = ROOT / "runtime/scripts/generate_tools_doc.py"
CONTRACTS = ROOT / "contracts/extensions/mcp/v1"
REPO = "https://github.com/SterlingJF/knowledge-mcp/blob/main"


def test_the_tools_doc_lists_every_tool_argument_and_result_schema():
    text = DOC.read_text()
    tools = json.loads((CONTRACTS / "tools.json").read_text())["tools"]
    assert "{/* BEGIN AUTO-GENERATED arguments */}" in text
    for tool in tools:
        assert f"| `{tool['name']}`" in text
        section = text.split(f"### `{tool['name']}`\n", 1)[1].split("\n###", 1)[0]
        required = tool["inputSchema"].get("required", [])
        for name in tool["inputSchema"].get("properties", {}):
            row = next(
                line for line in section.splitlines() if line.startswith(f"| `{name}` ")
            )
            cells = row.split(" | ")
            assert cells[2].strip() == ("yes" if name in required else "no"), row
        output = tool.get("outputSchema")
        if output:
            schema = output["$id"]
            assert (CONTRACTS / schema).is_file()
            assert f"]({REPO}/contracts/extensions/mcp/v1/{schema})" in text


def test_a_stale_tools_doc_fails_the_check_and_names_the_recipe(tmp_path):
    path = tmp_path / "tools.mdx"
    text = DOC.read_text().replace("`kb_get_document_type`", "`kb_obsolete_tool`", 1)
    path.write_text(text)
    done = subprocess.run(
        [sys.executable, str(GENERATOR), str(path), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert done.stderr == f"{path} is stale. Run just generate_mcp_tools_doc.\n"
    assert path.read_text() == text
