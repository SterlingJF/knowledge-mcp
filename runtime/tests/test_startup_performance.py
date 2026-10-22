from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from mcp.server.mcpserver.exceptions import ToolError

from knowledge_mcp import kbp, problems, schemas

RUNTIME = Path(__file__).resolve().parents[1]
SCHEMAS = RUNTIME / "knowledge_mcp" / "schemas_auto"

CLI_PROBE = """
import importlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
eager = sys.argv[2] == "eager"
if eager:
    for name in ("mcp.server.mcpserver.exceptions", "jsonschema",
                 "knowledge_mcp.schemas", "knowledge_mcp.models_auto.problem_schema"):
        importlib.import_module(name)

from click.testing import CliRunner
from knowledge_mcp.cli import kb

result = CliRunner().invoke(kb, sys.argv[3:], prog_name="kb")
assert result.exit_code == 0, result.exception
assert result.stdout
assert result.stderr == ""
if not eager:
    for name in ("mcp", "jsonschema", "pydantic", "knowledge_mcp.schemas",
                 "knowledge_mcp.models_auto.problem_schema"):
        assert name not in sys.modules, name
for name, module in tuple(sys.modules.items()):
    if name == "knowledge_mcp" or name.startswith("knowledge_mcp."):
        assert Path(module.__file__).resolve().is_relative_to(root), name
print(json.dumps([result.exit_code, result.stdout, result.stderr]))
"""


@pytest.mark.parametrize("args", [("--help",), ("--version",), ("setup", "--help")])
def test_cli_startup_imports_and_streams(args, tmp_path):
    outputs = []
    for mode in ("lazy", "eager"):
        done = subprocess.run(
            [sys.executable, "-B", "-c", CLI_PROBE, str(RUNTIME), mode, *args],
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert done.returncode == 0, done.stderr
        assert done.stderr == ""
        outputs.append(json.loads(done.stdout))
    assert outputs[0] == outputs[1]


def test_exception_identity_and_unwrapping():
    assert kbp.KbpMissing is problems.KbpMissing
    error = problems.Error("bad argument", code="argument-invalid", pointer="#/x")
    assert problems.from_exception(error, "example") is error
    wrapped = ToolError("wrapped")
    wrapped.__cause__ = error
    assert problems.from_exception(wrapped, "example") is error
    assert error.details() == {
        "type": problems.BASE + "argument-invalid",
        "title": schemas.title("argument-invalid"),
        "detail": "bad argument",
        "errors": [{"detail": "bad argument", "pointer": "#/x"}],
    }


@pytest.mark.parametrize("fallback", [False, True])
def test_generated_schema_loader_parity(fallback, monkeypatch):
    if fallback:
        monkeypatch.delattr(yaml, "CSafeLoader", raising=False)
    paths = sorted(SCHEMAS.glob("*.schema.yaml"))
    assert len(paths) == 16
    schemas.bundle.cache_clear()
    try:
        for path in paths:
            name = path.name.removesuffix(".schema.yaml")
            loaded = schemas.bundle(name)
            assert loaded == yaml.safe_load(path.read_text(encoding="utf-8"))
            assert schemas.bundle(name) is loaded
    finally:
        schemas.bundle.cache_clear()
