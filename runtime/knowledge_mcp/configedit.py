"""Preserve unrelated settings text when adding or removing server entries."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from json5.model import Node as ModelNode


class ConfigError(ValueError):
    """`line` is the line number of a syntax error, or None for errors with no line."""

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(f"line {line}: {message}" if line is not None else message)
        self.line = line


@dataclass
class Node:
    """Offsets count characters in the source text."""

    start: int
    end: int
    value: Any = None
    # For objects: (key, key offset, value node) for each member, in file order.
    members: list[tuple[str, int, Node]] = field(default_factory=list)


def _position(model: ModelNode, lines: list[int], *, end: bool = False) -> int:
    line = model.end_lineno if end else model.lineno
    column = model.end_col_offset if end else model.col_offset
    assert line is not None and column is not None
    return lines[line - 1] + column


def _source_node(model: ModelNode, text: str, lines: list[int]) -> Node:
    """Adapt json-five's source positions; keep edits on the original text."""
    from json5.model import (  # noqa: PLC0415 - defer JSONC startup.
        JSONArray,
        JSONObject,
    )

    start = _position(model, lines)
    end = _position(model, lines, end=True)
    node = Node(start, end)
    if isinstance(model, JSONObject):
        node.value = {}
        for key, value in model.key_value_pairs:
            begin = _position(key, lines)
            finish = _position(key, lines, end=True)
            name = json.loads(text[begin:finish])
            if not isinstance(name, str):
                message = "quoted object key expected"
                raise ConfigError(message, key.lineno)
            child = _source_node(value, text, lines)
            node.members.append((name, begin, child))
            node.value[name] = child.value
    elif isinstance(model, JSONArray):
        node.value = [_source_node(value, text, lines).value for value in model.values]
    else:
        # JSONC has JSON literals, not JSON5's additional string/number forms.
        def reject_constant(_constant: str) -> Any:
            message = "JSON number expected"
            raise ConfigError(message, model.lineno)

        node.value = json.loads(text[start:end], parse_constant=reject_constant)
    return node


def parse_json(text: str) -> Node:
    """Parse JSONC with json-five, preserving source positions for local edits."""
    if not text.strip():
        return Node(0, 0, {})
    from json5.loader import ModelLoader, loads  # noqa: PLC0415 - defer JSONC startup.
    from json5.utils import JSON5DecodeError  # noqa: PLC0415 - defer JSONC startup.

    try:
        model = loads(text, loader=ModelLoader())
    except JSON5DecodeError as error:
        line = error.token.lineno if error.token else text.count("\n") + 1
        raise ConfigError(str(error), line) from None
    lines = [0, *(match.end() for match in re.finditer("\n", text))]
    node = _source_node(model.value, text, lines)
    if not isinstance(node.value, dict):
        message = "expected a JSON object at the top of the file"
        raise ConfigError(message)
    return node


def json_value(text: str) -> dict[str, Any]:
    value = parse_json(text).value
    assert isinstance(value, dict)
    return value


def _child(node: Node, key: str) -> Node | None:
    for name, _begin, child in node.members:
        if name == key:
            return child
    return None


def json_entry(text: str, path: tuple[str, ...], name: str) -> Any:
    """Return None when the object at `path` or the entry is missing."""
    node: Node | None = parse_json(text)
    for key in path:
        node = (
            _child(node, key)
            if node is not None and isinstance(node.value, dict)
            else None
        )
    if node is None or not isinstance(node.value, dict):
        return None
    return node.value.get(name)


def _indent_of(text: str, position: int) -> str:
    line = text.rfind("\n", 0, position) + 1
    match = re.match(r"[ \t]*", text[line:])
    assert match is not None
    return match.group()


def _unit(text: str) -> str:
    """Indentation of the first indented line, or two spaces when no line is indented."""
    match = re.search(r"\n([ \t]+)\S", text)
    return match.group(1) if match else "  "


def _insertion_node(root: Node, path: tuple[str, ...]) -> tuple[Node, list[str]]:
    node = root
    missing: list[str] = []
    for index, key in enumerate(path):
        child = _child(node, key)
        if child is None:
            missing = list(path[index:])
            break
        if not isinstance(child.value, dict):
            message = f"{'.'.join(path[: index + 1])} is not an object"
            raise ConfigError(message)
        node = child
    return node, missing


def json_insert(
    text: str, path: tuple[str, ...], name: str, entry: Any
) -> tuple[str, str]:
    """Insert `name: entry` as the first member of the object at `path`, creating missing objects.

    Return the new text and the inserted piece. Raise `ConfigError` when the entry already exists
    or a key on `path` is not an object.
    """
    if not text.strip():
        value: Any = {name: entry}
        for key in reversed(path):
            value = {key: value}
        piece = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        return text + piece, piece
    node, missing = _insertion_node(parse_json(text), path)
    unit = _unit(text)
    if not missing and name in node.value:
        message = f"an entry named {name!r} already exists"
        raise ConfigError(message)
    value = {name: entry}
    for key in reversed(missing):
        value = {key: value}
    [(key, member)] = value.items()
    outer = _indent_of(text, node.start)
    if node.members:
        first = node.members[0][1]
        inner = _indent_of(text, first)
        multiline = "\n" in text[node.start : first]
    else:
        first = node.start + 1
        inner = outer + unit
        multiline = True
    if multiline:
        rendered = json.dumps(member, indent=unit, ensure_ascii=False).replace(
            "\n", "\n" + inner
        )
    else:
        rendered = json.dumps(member, ensure_ascii=False)
    body = f"{json.dumps(key, ensure_ascii=False)}: {rendered}"
    if not node.members:
        piece = f"\n{inner}{body}\n{outer}"
    elif multiline:
        piece = f"{body},\n{inner}"
    else:
        piece = f"{body}, "
    new = text[:first] + piece + text[first:]
    json_value(new)
    return new, piece


def json_remove(text: str, path: tuple[str, ...], name: str, piece: str | None) -> str:
    """When `piece` appears exactly once, delete it to undo the insertion byte for byte.

    Otherwise delete the `name` member at `path`.
    """
    if piece and text.count(piece) == 1:
        new = text.replace(piece, "", 1)
        if new.strip():
            json_value(new)
        return new
    node: Node | None = parse_json(text)
    for key in path:
        node = _child(node, key) if node is not None else None
    if node is None or not isinstance(node.value, dict) or name not in node.value:
        return text
    from json5.tokenizer import tokenize  # noqa: PLC0415 - defer JSONC startup.

    members = node.members
    index = next(i for i, (key, _begin, _child) in enumerate(members) if key == name)
    _key, begin, child = members[index]
    # Remove only this member and one separator. Comments and whitespace between
    # members belong to the user's file, including comments in an otherwise empty object.
    limit = members[index + 1][1] if index + 1 < len(members) else node.end - 1
    commas = [
        child.end + token.index
        for token in tokenize(text[child.end : limit])
        if token.type == "COMMA"
    ]
    spans = [(begin, child.end)]
    if commas:
        spans.append((commas[0], commas[0] + 1))
    elif index > 0:
        previous = members[index - 1][2].end
        spans.extend(
            (previous + token.index, previous + token.end)
            for token in tokenize(text[previous:begin])
            if token.type == "COMMA"
        )
    new = text
    for start, end in sorted(spans, reverse=True):
        new = new[:start] + new[end:]
    json_value(new)
    return new


def empty_chain(text: str, path: tuple[str, ...]) -> bool:
    """True when the text holds only the objects along `path`, with no other members."""
    if not text.strip():
        return True
    try:
        value: Any = json_value(text)
    except ConfigError:
        return False
    for key in path:
        if value == {}:
            return True
        if not isinstance(value, dict) or set(value) != {key}:
            return False
        value = value[key]
    return bool(value == {})


_BARE = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(key: str) -> str:
    return key if _BARE.match(key) else json.dumps(key)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    message = f"can't write {value!r} as TOML"
    raise ConfigError(message)


def toml_entry(text: str, table: str, name: str) -> Any:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(error.msg, error.lineno) from None
    servers = data.get(table, {})
    return servers.get(name) if isinstance(servers, dict) else None


def toml_insert(
    text: str, table: str, name: str, entry: dict[str, Any]
) -> tuple[str, str]:
    """Append the entry as a `[table.name]` table.

    Return the new text and the appended piece. Raise `ConfigError` when the entry already exists
    or the text is not valid TOML.
    """
    if toml_entry(text, table, name) is not None:
        message = f"an entry named {name!r} already exists"
        raise ConfigError(message)
    lines = [f"[{table}.{_toml_key(name)}]"]
    lines += [
        f"{_toml_key(key)} = {_toml_value(value)}" for key, value in entry.items()
    ]
    block = "\n".join(lines) + "\n"
    if not text.strip():
        piece = block
    else:
        piece = ("" if text.endswith("\n") else "\n") + "\n" + block
    new = text + piece
    try:
        tomllib.loads(new)
    except tomllib.TOMLDecodeError as error:
        message = f"invalid TOML after adding the table: {error}"
        raise ConfigError(message) from None
    return new, piece


def toml_remove(text: str, table: str, name: str, piece: str | None) -> str:
    """When `piece` appears exactly once, delete it to undo the insertion byte for byte.

    Otherwise remove sections with bare or double-quoted entry names under a bare parent table name, including subtables.
    Keep inline assignments and other header forms.
    """
    if piece and text.count(piece) == 1:
        return text.replace(piece, "", 1)
    if toml_entry(text, table, name) is None:
        return text
    header = re.compile(
        rf"^[ \t]*\[[ \t]*{re.escape(table)}[ \t]*\.[ \t]*(?:{re.escape(name)}|\"{re.escape(name)}\")[ \t]*(?:\.[^\]]*)?\][ \t]*(?:#.*)?$"
    )
    any_header = re.compile(r"^[ \t]*\[")
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    dropping = False
    for line in lines:
        if any_header.match(line):
            dropping = bool(header.match(line.rstrip("\r\n")))
        if not dropping:
            kept.append(line)
    new = "".join(kept)
    tomllib.loads(new)
    return new
