"""Split Markdown into headings, list items, fenced code blocks and paragraphs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Maximum length of `opening` in characters, excluding the trailing `…`.
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


Passage = tuple[str, int, int, str, int]


@dataclass
class _Scanner:
    found: list[Passage] = field(default_factory=list)
    current: _Open | None = None

    def close(self, last: int, kind: str | None = None, level: int = 0) -> None:
        if self.current is not None:
            self.found.append(
                (
                    kind or self.current.kind,
                    self.current.first,
                    last,
                    self.current.lines[0],
                    level,
                )
            )
        self.current = None

    def consume(self, number: int, line: str) -> None:
        if self.current is not None and self.current.kind == "code":
            self.current.lines.append(line)
            if re.fullmatch(
                rf"{re.escape(self.current.fence[0])}{{{len(self.current.fence)},}}",
                line.strip(),
            ):
                self.close(number)
            return
        if not line.strip():
            self.close(number - 1)
            return
        fence = _FENCE.match(line)
        if fence:
            self.close(number - 1)
            self.current = _Open("code", number, [line], fence.group(1))
            return
        underline = _UNDERLINE.match(line)
        if underline and self.current is not None and self.current.kind == "paragraph":
            self.close(number, "heading", 1 if underline.group(1)[0] == "=" else 2)
            return
        if _RULE.match(line):
            self.close(number - 1)
            return
        heading = _ATX.match(line)
        if heading:
            self.close(number - 1)
            self.found.append(("heading", number, number, line, len(heading.group(1))))
            return
        if _ITEM.match(line):
            self.close(number - 1)
            self.current = _Open("list-item", number, [line])
        elif self.current is None:
            self.current = _Open("paragraph", number, [line])
        else:
            self.current.lines.append(line)


def split(text: str) -> list[dict[str, Any]]:
    scanner = _Scanner()
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for number, line in enumerate(lines, start=1):
        scanner.consume(number, line)
    if scanner.current is not None:
        # A trailing newline adds no line.
        last = len(lines) - 1 if lines[-1] == "" else len(lines)
        scanner.close(max(last, scanner.current.first))

    return _passages(scanner.found)


def _passages(found: list[Passage]) -> list[dict[str, Any]]:
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
    flat = " ".join(line.split())
    if len(flat) <= OPENING:
        return flat
    cut = flat[:OPENING]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut) + "…"
