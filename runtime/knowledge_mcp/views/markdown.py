"""Render cards as markdown."""

from __future__ import annotations

from datetime import UTC, datetime
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


def when(time: str) -> str:
    """An ISO timestamp as `Oct 18, 17:42 UTC`."""
    moment = datetime.fromisoformat(time.replace("Z", "+00:00")).astimezone(UTC)
    return f"{moment:%b} {moment.day}, {moment:%H:%M} UTC"


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
    if "line_number" not in source:
        return code(file)
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


def _meta(answer: dict[str, Any]) -> list[str]:
    parts = []
    if "document_type" in answer:
        parts.append(_line(answer["document_type"]["label"]))
    if "reader" in answer:
        reader = answer["reader"]
        guess = "" if reader["confirmed"] else " (reader is a guess)"
        parts.append(f"for {_line(reader['label'])}{guess}")
    lines = ["", " · ".join(parts)] if parts else []
    if "filing" in answer:
        filing = answer["filing"]
        rule = filing["naming_rule"]
        note = f"named by {_line(rule)}" if rule else "no naming rule"
        line = f"Saved as {code(filing['path'])} · {note}"
        if "reason" in filing:
            line += f": {_line(filing['reason'])}"
        lines += ["", line]
    return lines


def proposal(answer: dict[str, Any], layout: Layout) -> str:
    """`list` is for terminals, which can't scroll a wide table sideways."""
    lines = [
        f"{code('PROPOSED CHANGES')} · {code('Nothing saved')}",
        "",
        f"**{_line(answer['summary'])}**",
        *_meta(answer),
        "",
        *(_list if layout == "list" else _table)(answer["rows"]),
    ]
    for left in answer.get("left_out", []):
        lines += ["", f"⊘ {code(left['file'])} left out: {_line(left['reason'])}"]
    for question in answer.get("open_questions", []):
        label = question.get("label")
        named = f"**{_line(label)}** · " if label else ""
        lines += ["", f"? Needs you · {named}no source: {_line(question['text'])}"]
    return "\n".join(lines) + "\n"


def _name(answer: dict[str, Any]) -> str:
    return PurePosixPath(answer["location"]).name


def _title(entry: dict[str, Any]) -> str:
    if entry["allowed_by"]["basis"] == "accepted_change":
        return "Approved revision"
    return "Edit"


def _changes(found: dict[str, Any]) -> list[str]:
    hunks = found["hunks"]
    lines = [f"{hunks} change" + ("" if hunks == 1 else "s"), ""]
    for line in found["lines"]:
        text = _line(line["text"])
        if line["change"] == "removed":
            lines.append(f"- ~~{text}~~" if text else "- (blank line removed)")
        else:
            lines.append(f"- {text}" if text else "- (blank line added)")
    if found["more"]:
        lines.append(f"- … and {found['more']} more changed lines")
    return lines


def saved(answer: dict[str, Any]) -> str:
    name = code(_name(answer))
    verb = "creation of" if answer.get("created") else "edit to"
    text = (
        f"{code('Saved')} · **{_title(answer)} saved**\n\n"
        f"The {verb} {name} is recorded.\n"
    )
    if answer.get("undoes"):
        text += f"\nIt undoes the edit from {when(answer['undoes']['time'])}.\n"
    found = answer.get("changes")
    if found and found["hunks"]:
        heading, *rest = _changes(found)
        text += "\n" + "\n".join([f"{name} · {heading}", *rest]) + "\n"
    return text


def pickup(answer: dict[str, Any]) -> str | None:
    if not answer["edits"]:
        return None
    eyebrow = _title(answer["edits"][-1]).upper()
    return f"{code(eyebrow)} · {code(_name(answer))}\n"


JOIN = " · "
ARROW = " → "

MOVE_BADGES = {
    "permission_needed": "Needs your OK",
    "blocked": "Needs your choice",
    "ready": "Approved",
    "texts_needed": "Nothing saved",
    "unchanged": "Nothing saved",
}


def _count(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _folder(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return "/" if parent == "." else f"{parent}/"


def _move(move: dict[str, Any]) -> str:
    old, new = PurePosixPath(move["old_path"]), PurePosixPath(move["path"])
    target = _folder(move["path"])
    if old.name != new.name:
        target += f" as {code(new.name)}"
    return f"{code(move['old_path'])}{ARROW}{target}"


def _link(link: dict[str, Any]) -> str:
    after = code(link["replacement"])
    if "line" in link and "text" in link:
        note = code(f"{link['source_path']}:{link['line']}")
        return f"{note}{JOIN}{code(link['text'])}{ARROW}{after}"
    before = code(link["target_before"])
    return f"{code(link['source_path'])}{JOIN}{before}{ARROW}{after}"


def _numbered(items: list[str]) -> list[str]:
    return [f"{n}. {item}" for n, item in enumerate(items, start=1)]


def _choice(choice: dict[str, Any]) -> str:
    if choice["action"] == "skip_move":
        return f"Skip this file ({code(choice['path'])})"
    return f"Link to {code(choice['path'])}"


def _blocker(issue: dict[str, Any]) -> str:
    choices = issue.get("choices", [])
    return "".join([_line(issue["detail"]), *(f"\n   - {_choice(c)}" for c in choices)])


def _heading(answer: dict[str, Any], files: int) -> list[str]:
    lines = []
    if "summary" in answer:
        lines += [f"## {_line(answer['summary'])}", ""]
    if "folder" in answer:
        new = _count(files, "new file", "new files")
        lines += [f"{code(answer['folder'])}{JOIN}{new}", ""]
    return lines


def moves(answer: dict[str, Any]) -> str:
    """The move plan: moves, repaired links, blockers, then what the person can say next."""
    status = answer["status"]
    rows = answer["moves"]
    repaired = [link for link in answer["links"] if link["replacement"] is not None]
    notes = {link["source_path"] for link in repaired}
    renames = sum(
        PurePosixPath(m["old_path"]).name != PurePosixPath(m["path"]).name for m in rows
    )
    summary = [_count(len(rows), "move", "moves")]
    if renames:
        summary.append(_count(renames, "rename", "renames"))
    summary.append(_count(len(repaired), "link repaired", "links repaired"))
    if notes:
        summary.append(_count(len(notes), "note", "notes"))
    stays = answer.get("stays", [])
    rules = {n["path"]: n["rule"] for n in answer.get("naming", [])}
    lines = [f"{code('PROPOSED MOVES')} · {code(MOVE_BADGES[status])}", ""]
    lines += _heading(answer, len(rows) + len(stays))
    lines.append(f"**{JOIN.join(summary)}**")
    if rows:
        lines += [
            "",
            f"**Moves ({len(rows)})**",
            "",
            *_numbered(
                [
                    _move(m)
                    + (f"{JOIN}{rules[m['path']]}" if m["path"] in rules else "")
                    for m in rows
                ]
            ),
        ]
    if stays:
        stay = "file stays" if len(stays) == 1 else "files stay"
        lines += [
            "",
            f"**{len(stays)} {stay} where {'it is' if len(stays) == 1 else 'they are'}**",
            "",
            *_numbered(
                [
                    f"Stays{JOIN}{code(s['path'])}{JOIN}{_line(s['reason'])}"
                    for s in stays
                ]
            ),
        ]
    if repaired:
        lines += [
            "",
            f"**Links ({len(repaired)})**",
            "",
            *_numbered([_link(link) for link in repaired]),
        ]
    if answer["issues"]:
        lines += [
            "",
            f"**Blockers ({len(answer['issues'])})**",
            "",
            *_numbered([_blocker(issue) for issue in answer["issues"]]),
        ]
    move = f"Move {_count(len(rows), 'file', 'files')}"
    if status == "permission_needed":
        lines += [
            "",
            f"Waits for you because it moves files and edits links in {_count(len(notes), 'note', 'notes')}. You can undo it afterwards.",
            "",
            f"Say “{move}” or “Not now”.",
        ]
    elif status == "blocked":
        lines += [
            "",
            "Move stays off until each blocker has a choice.",
            "",
            "Say your choice for each blocker, or “Not now”.",
        ]
    return "\n".join(lines) + "\n"


CONVENTION_BADGES = {
    "permission_needed": "Nothing saved",
    "ready": "Approved",
    "unchanged": "Nothing saved",
}


def _part(part: dict[str, Any]) -> str:
    kind = part["part"]
    if kind == "content":
        return "title"
    if kind == "document_type":
        return "type"
    if kind == "literal":
        return str(part["value"])
    return str(part["property"]) if kind == "property" else "date"


def _filing(change: dict[str, Any]) -> str:
    folder = "".join(
        f"{item}/" if isinstance(item, str) else f"{{{_part(item)}}}/"
        for item in change["folder"]
    )
    name = JOIN.join(_part(part) for part in change["name"]["parts"])
    return JOIN.join([code(folder or "/"), name])


def _convention(change: dict[str, Any]) -> str:
    kind = code(change["document_type"])
    if change["change"] == "remove":
        return f"{kind}{JOIN}removed"
    return f"{kind}{JOIN}{_filing(change)}"


def conventions(answer: dict[str, Any]) -> str:
    """Proposed conventions: one numbered row per change, then what the person can say next."""
    status = answer["status"]
    changes = answer["changes"]
    where = answer.get("folder") or _name(answer) or answer["location"]
    lines = [
        f"{code('PROPOSED CONVENTIONS')} · {code(CONVENTION_BADGES[status])}",
        "",
        f"**Naming and filing for {_line(where)}**",
        "",
    ]
    if changes:
        lines += _numbered([_convention(c) for c in changes])
    else:
        lines.append("No changes")
    lines += ["", "Existing files unchanged until a move."]
    if status == "permission_needed":
        lines += ["", "Say “Save accepted”, which to drop, or “Not now”."]
    return "\n".join(lines) + "\n"
