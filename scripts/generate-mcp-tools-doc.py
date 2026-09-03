# File: scripts/generate-mcp-tools-doc.py

"""Regenerate or check derived tool tables in docs/mcp-tools.md."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / 'docs' / 'mcp-tools.md'

sys.path.insert(0, str(REPO / 'mcp'))


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
    flat = ' '.join(text.split())
    match = re.match(r'(.+?\.)(?:\s|$)', flat)
    return match.group(1) if match else flat


def table(tools: list[dict]) -> str:
    """Markdown table for the collected tools."""
    rows = '\n'.join(
        f"| `{t['name']}` | {first_sentence(t['description'])} |" for t in tools
    )
    return f'| Tool | What it does |\n| --- | --- |\n{rows}'


def main() -> int:
    """Regenerate or check the doc."""
    from app.tools import artifacts, files, universes, vaults

    sections = {}
    for heading, module in (
        ('## Artifacts', artifacts),
        ('## Files', files),
        ('## Universes', universes),
        ('## Vaults', vaults),
    ):
        collector = Collector()
        module.register(collector)
        sections[heading] = table(collector.tools)

    text = DOC.read_text()
    for heading, new_table in sections.items():
        # Replace first markdown table after heading.
        pattern = re.compile(
            rf'({re.escape(heading)}\n\n)\| Tool \| What it does \|\n\| --- \| --- \|\n(?:\|.*\n)+',
        )
        if not pattern.search(text):
            print(f'no table found under {heading!r}', file=sys.stderr)
            return 2
        text = pattern.sub(lambda m: m.group(1) + new_table + '\n', text)

    if '--check' in sys.argv:
        if text != DOC.read_text():
            print('docs/mcp-tools.md is stale; regenerate it.', file=sys.stderr)
            return 1
        print('docs/mcp-tools.md is current.')
        return 0

    DOC.write_text(text)
    print('docs/mcp-tools.md regenerated.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
