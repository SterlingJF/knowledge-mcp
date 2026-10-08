# File: mcp-server/scripts/generate_tools_doc.py

"""Regenerate or check the intro and the tool tables in the tools doc the caller names."""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(MODULE))

INTRO = re.compile(
    r"(<!-- BEGIN AUTO-GENERATED intro -->\n\n).*?(\n\n<!-- END AUTO-GENERATED intro -->)",
    re.DOTALL,
)


class Collector:
    """Collect @mcp.tool registrations."""

    def __init__(self) -> None:
        self.tools: list[dict] = []

    def tool(self, **kwargs):
        def decorate(function):
            self.tools.append(kwargs)
            return function

        return decorate


def first_sentence(text: str) -> str:
    """First sentence of the flattened text."""
    flat = " ".join(text.split())
    match = re.match(r"(.+?\.)(?:\s|$)", flat)
    return match.group(1) if match else flat


def display_width(text: str) -> int:
    """Columns the text fills: wide characters take two, combining marks none."""
    return sum(
        0
        if unicodedata.combining(char)
        else 2
        if unicodedata.east_asian_width(char) in "WF"
        else 1
        for char in text
    )


def table(tools: list[dict]) -> str:
    """Markdown table for the collected tools, columns padded as Prettier pads them."""
    rows = [("Tool", "What it does")] + [
        (f"`{t['name']}`", first_sentence(t["description"])) for t in tools
    ]
    widths = [max(3, *(display_width(row[i]) for row in rows)) for i in range(2)]

    def line(cells: tuple[str, ...]) -> str:
        padded = (
            cell + " " * (width - display_width(cell))
            for cell, width in zip(cells, widths, strict=True)
        )
        return "| " + " | ".join(padded) + " |"

    divider = tuple("-" * width for width in widths)
    return "\n".join(line(row) for row in (rows[0], divider, *rows[1:]))


def intro(count: int, revision: str) -> str:
    """The tool count and the MCP revision the server serves."""
    link = f"https://modelcontextprotocol.io/docs/{revision}/getting-started/intro"
    return (
        f"The server has {count} tools, one per operation. "
        f"It serves MCP [revision {revision}]({link}) and refuses every other revision."
    )


def parse_args() -> argparse.Namespace:
    """The doc path, and whether to check instead of write."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "doc", type=Path, help="the tools doc, such as docs/mcp-tools.md"
    )
    parser.add_argument("--check", action="store_true", help="fail if the doc is stale")
    return parser.parse_args()


def main() -> int:
    """Regenerate or check the doc."""
    args = parse_args()
    doc: Path = args.doc

    from app.settings import MCP_REVISION
    from app.tools import artifacts, files, universes, vaults

    count = 0
    sections = {}
    for heading, module in (
        ("## Artifacts", artifacts),
        ("## Files", files),
        ("## Universes", universes),
        ("## Vaults", vaults),
    ):
        collector = Collector()
        module.register(collector)
        count += len(collector.tools)
        sections[heading] = table(collector.tools)

    text = doc.read_text()
    if not INTRO.search(text):
        print("no AUTO-GENERATED intro region found", file=sys.stderr)
        return 2
    text = INTRO.sub(
        lambda m: m.group(1) + intro(count, MCP_REVISION) + m.group(2), text
    )
    for heading, new_table in sections.items():
        # Replace the first markdown table after the heading, padded or not.
        pattern = re.compile(
            rf"({re.escape(heading)}\n\n)\| Tool +\| What it does +\|\n\|[ -]+\|[ -]+\|\n(?:\|.*\n)+",
        )
        if not pattern.search(text):
            print(f"no table found under {heading!r}", file=sys.stderr)
            return 2
        text = pattern.sub(lambda m, rows=new_table: m.group(1) + rows + "\n", text)

    if args.check:
        if text != doc.read_text():
            print(f"{doc} is stale; regenerate it.", file=sys.stderr)
            return 1
        print(f"{doc} is current.")
        return 0

    doc.write_text(text)
    print(f"{doc} regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
