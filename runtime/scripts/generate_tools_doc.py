"""Write or check the generated regions of an MCP tools doc from contracts/extensions/mcp/v1/tools.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "extensions" / "mcp" / "v1"
RECIPE = "just generate_mcp_tools_doc"


def first_sentence(text: str) -> str:
    flat = " ".join(text.split())
    match = re.match(r"(.+?\.)(?:\s|$)", flat)
    return match.group(1) if match else flat


def display_width(text: str) -> int:
    """Count two columns per wide character, zero per combining mark and one column per remaining character."""
    return sum(
        0
        if unicodedata.combining(char)
        else 2
        if unicodedata.east_asian_width(char) in "WF"
        else 1
        for char in text
    )


def table(rows: list[tuple[str, ...]]) -> str:
    """A Markdown table with Prettier's padding."""
    widths = [
        max(3, *(display_width(row[i]) for row in rows)) for i in range(len(rows[0]))
    ]

    def line(cells: tuple[str, ...]) -> str:
        padded = (
            cell + " " * (width - display_width(cell))
            for cell, width in zip(cells, widths, strict=True)
        )
        return "| " + " | ".join(padded) + " |"

    divider = tuple("-" * width for width in widths)
    return "\n".join(line(row) for row in (rows[0], divider, *rows[1:]))


def cell(text: str) -> str:
    """Text for one table cell: one line, pipes escaped."""
    return " ".join(text.split()).replace("|", "\\|")


def listing(values: list[Any]) -> str:
    quoted = [f"`{value}`" for value in values]
    return (
        quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " or " + quoted[-1]
    )


def kind(schema: dict[str, Any]) -> str:
    """Render a `$ref` as a link to its Shapes table."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return f"[{name}](#{name.lower()})"
    if "anyOf" in schema:
        return " or ".join(kind(option) for option in schema["anyOf"])
    if "enum" in schema or "const" in schema:
        return listing(schema["enum"] if "enum" in schema else [schema["const"]])
    if schema.get("type") == "array":
        return f"list of {kind(schema.get('items', {}))}"
    if "pattern" in schema:
        return f"string, pattern `{schema['pattern']}`"
    types = schema.get("type", "any")
    return " or ".join(types) if isinstance(types, list) else str(types)


def fields(schema: dict[str, Any], label: str) -> str:
    required = set(schema.get("required", []))
    rows = [(label, "Type", "Required", "Meaning")] + [
        (
            f"`{name}`",
            cell(kind(prop)),
            "yes" if name in required else "no",
            cell(prop.get("description", "")),
        )
        for name, prop in schema.get("properties", {}).items()
    ]
    if len(rows) > 1:
        return table(rows)
    return (
        "No arguments." if schema.get("type") == "object" else f"Type: {kind(schema)}."
    )


def regions(tools: list[dict[str, Any]]) -> dict[str, str]:
    summary = [("Tool", "Purpose", "Result")]
    arguments: list[str] = []
    shapes: dict[str, dict[str, Any]] = {}
    for tool in tools:
        output = tool.get("outputSchema")
        if output and "$id" not in output:
            message = f"tools.json: {tool['name']} has an outputSchema with no $id. Run just generate_contract_snapshots."
            raise SystemExit(message)
        result = (
            f"[{output['$id']}](../contracts/extensions/mcp/v1/{output['$id']})"
            if output
            else "kbp's output, as is"
        )
        summary.append(
            (f"`{tool['name']}`", cell(first_sentence(tool["description"])), result)
        )
        arguments.append(
            f"### `{tool['name']}`\n\n{fields(tool['inputSchema'], 'Argument')}"
        )
        for name, shape in tool["inputSchema"].get("$defs", {}).items():
            if shapes.setdefault(name, shape) != shape:
                message = f"tools.json: two tools define different shapes named {name}. Give the conflicting definitions distinct names in their source. Run just generate_contract_types, then just generate_contract_snapshots."
                raise SystemExit(message)
    return {
        "intro": (
            "The server serves MCP over stdio and opens no network port. Harnesses with a "
            "knowledge-mcp plugin start the server through the plugin. Other harnesses run "
            "`kb mcp`."
        ),
        "tools": table(summary),
        "arguments": "\n\n".join(arguments),
        "shapes": "\n\n".join(
            f"### {n}\n\n{fields(s, 'Field')}" for n, s in sorted(shapes.items())
        ),
    }


def main() -> int:
    """With --check, write nothing and exit 1 when the doc is stale.

    Exit 2 when a region is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "doc", type=Path, help="the tools doc, such as docs/mcp-tools.md"
    )
    parser.add_argument(
        "--check", action="store_true", help="fail when the doc is stale"
    )
    args = parser.parse_args()
    listed = json.loads((CONTRACTS / "tools.json").read_text())
    tools = listed["tools"] if isinstance(listed, dict) else listed
    text = args.doc.read_text()
    updated = text
    for name, body in regions(tools).items():
        pattern = re.compile(
            rf"(<!-- BEGIN AUTO-GENERATED {name} -->\n\n).*?(\n\n<!-- END AUTO-GENERATED {name} -->)",
            re.DOTALL,
        )
        if not pattern.search(updated):
            print(
                f"{args.doc}: no {name} region. Add the BEGIN and END AUTO-GENERATED {name} lines.",
                file=sys.stderr,
            )
            return 2
        updated = pattern.sub(
            lambda match, body=body: match.group(1) + body + match.group(2), updated
        )
    if args.check:
        if updated != text:
            print(f"{args.doc} is stale. Run {RECIPE}.", file=sys.stderr)
            return 1
        print(f"{args.doc} is current.")
        return 0
    args.doc.write_text(updated)
    print(f"Wrote {args.doc}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
