"""Render cards as markdown."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Literal

type Layout = Literal["list", "table"]

MARKS = {
    "supported": "● Supported",
    "partly": "◐ Partly answered",
    "conflicting": "✕ Conflicting",
    "suggested": "◆ Suggested",
}
PLACE = " \N{SINGLE RIGHT-POINTING ANGLE QUOTATION MARK} "


def code(text: str) -> str:
    """A code span that holds `text` even when it contains backticks."""
    fence = "`"
    while fence in text:
        fence += "`"
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def _line(text: str) -> str:
    return " ".join(text.split())


def _cell(text: str) -> str:
    return _line(text).replace("|", "\\|")


def _text(value: dict[str, Any] | None) -> str:
    if value is None:
        return "—"
    label = value.get("label")
    text = _cell(value["text"])
    return f"**{_cell(label)}:** {text}" if label else text


def _source(source: dict[str, Any]) -> str:
    if "said" in source:
        return "you, today"
    file = source["file"]
    if "place" in source:
        return code(file + PLACE + source["place"])
    return code(f"{file}:{source['line_number']}")


def _sources(row: dict[str, Any]) -> str:
    return " · ".join(_source(source) for source in row["sources"])


def _table(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["| ID | Current | Proposed | Source |", "| --- | --- | --- | --- |"]
    for number, row in enumerate(rows, start=1):
        proposed = _text(row["proposed"])
        if "mark" in row:
            proposed = f"{MARKS[row['mark']]} · {proposed}"
        current = _text(row.get("current"))
        lines.append(f"| C{number} | {current} | {proposed} | {_sources(row)} |")
    return lines


def _list(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for number, row in enumerate(rows, start=1):
        proposed, current = row["proposed"], row.get("current")
        label = proposed.get("label") or (current or {}).get("label")
        heading = [f"**C{number}**"]
        if "mark" in row:
            heading.append(MARKS[row["mark"]])
        if label:
            heading.append(f"**{_line(label)}**")
        now = "—"
        if current is not None:
            now = _line(current["text"])
            if current.get("label") not in (None, label):
                now = f"{_line(current['label'])}: {now}"
        if lines:
            lines.append("")
        lines += [
            " · ".join(heading),
            "",
            f"- Now: {now}",
            f"- Proposed: {_line(proposed['text'])}",
            f"- {_sources(row)}",
        ]
    return lines


def proposal(answer: dict[str, Any], layout: Layout) -> str:
    """`list` is for terminals, which can't scroll a wide table sideways."""
    lines = [
        f"{code('PROPOSED CHANGES')} · {code('Nothing saved')}",
        "",
        f"**{_line(answer['summary'])}**",
        "",
        *(_list if layout == "list" else _table)(answer["rows"]),
    ]
    for left in answer.get("left_out", []):
        lines += ["", f"⊘ {code(left['file'])} left out: {_line(left['reason'])}"]
    return "\n".join(lines) + "\n"


def _name(answer: dict[str, Any]) -> str:
    return PurePosixPath(answer["location"]).name


def _title(entry: dict[str, Any]) -> str:
    if entry["allowed_by"]["basis"] == "accepted_change":
        return "Approved revision"
    return "Edit"


def saved(answer: dict[str, Any]) -> str:
    return (
        f"{code('Saved')} · **{_title(answer)} saved**\n\n"
        f"The edit to {code(_name(answer))} is recorded.\n"
    )


def pickup(answer: dict[str, Any]) -> str | None:
    if not answer["edits"]:
        return None
    eyebrow = _title(answer["edits"][-1]).upper()
    return f"{code(eyebrow)} · {code(_name(answer))}\n"
