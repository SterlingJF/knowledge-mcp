"""The passages an outside document's text splits into, by line, for the agent to mark.

A passage is a heading (`#` lines, or a line underlined with `=` or `-`), a list item with its
continuation lines, a fenced code block kept whole, or a paragraph: a run of other lines between
blank lines. A line of three or more `-`, `*` or `_` alone separates passages and is none.
Nothing here judges what a passage says: an instruction inside the text is a passage like any
other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# The longest opening shown for a passage, in characters, before the cut mark.
OPENING = 80

_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]|$)")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_RULE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_UNDERLINE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?:[ \t]+|$)")


@dataclass
class _Open:
    kind: str
    first: int
    lines: list[str] = field(default_factory=list)
    fence: str = ""


def split(text: str) -> list[dict[str, Any]]:
    """Each passage: id, kind, first and last line, opening words, and the heading above."""
    found: list[tuple[str, int, int, str, int]] = []
    current: _Open | None = None

    def close(last: int, kind: str | None = None, level: int = 0) -> None:
        nonlocal current
        if current is not None:
            found.append(
                (kind or current.kind, current.first, last, current.lines[0], level)
            )
        current = None

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for number, line in enumerate(lines, start=1):
        if current is not None and current.kind == "code":
            current.lines.append(line)
            if re.fullmatch(
                rf"{re.escape(current.fence[0])}{{{len(current.fence)},}}", line.strip()
            ):
                close(number)
            continue
        if not line.strip():
            close(number - 1)
            continue
        fence = _FENCE.match(line)
        if fence:
            close(number - 1)
            current = _Open("code", number, [line], fence.group(1))
            continue
        underline = _UNDERLINE.match(line)
        if underline and current is not None and current.kind == "paragraph":
            close(number, "heading", 1 if underline.group(1)[0] == "=" else 2)
            continue
        if _RULE.match(line):
            close(number - 1)
            continue
        heading = _ATX.match(line)
        if heading:
            close(number - 1)
            found.append(("heading", number, number, line, len(heading.group(1))))
            continue
        if _ITEM.match(line):
            close(number - 1)
            current = _Open("list-item", number, [line])
            continue
        if current is None:
            current = _Open("paragraph", number, [line])
        else:
            current.lines.append(line)
    if current is not None:
        # An unclosed code block runs to the last line; text has no line after its final newline.
        last = len(lines) - 1 if lines[-1] == "" else len(lines)
        close(max(last, current.first))

    passages: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    for index, (kind, first, last, line, level) in enumerate(found, start=1):
        if kind == "heading":
            while headings and headings[-1][0] >= level:
                headings.pop()
        passages.append(
            {
                "id": f"p{index}",
                "kind": kind,
                "lines": [first, last],
                "opening": opening(line),
                "under": headings[-1][1] if headings else None,
            }
        )
        if kind == "heading":
            headings.append((level, f"p{index}"))
    return passages


def opening(line: str) -> str:
    """The line's first words, spaces collapsed, cut at a word with `…` past `OPENING`."""
    flat = " ".join(line.split())
    if len(flat) <= OPENING:
        return flat
    cut = flat[:OPENING]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut) + "…"
