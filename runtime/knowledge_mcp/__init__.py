"""The knowledge-mcp MCP server and the kb command line."""

from __future__ import annotations

import tomllib
from importlib import metadata
from pathlib import Path


def version() -> str:
    """Fall back to pyproject.toml when the package is not installed, as in the plugin folder."""
    try:
        return metadata.version("knowledge-mcp")
    except metadata.PackageNotFoundError:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return str(project["project"]["version"])
