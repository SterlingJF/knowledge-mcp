"""Preserve unrelated settings text when adding or removing server entries."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any


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


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0

    def fail(self, message: str) -> ConfigError:
        line = self.text.count("\n", 0, self.at) + 1
        return ConfigError(message, line)

    def blank(self) -> None:
        text = self.text
        while self.at < len(text):
            char = text[self.at]
            if char in " \t\r\n﻿":
                self.at += 1
            elif text.startswith("//", self.at):
                end = text.find("\n", self.at)
                self.at = len(text) if end < 0 else end
            elif text.startswith("/*", self.at):
                end = text.find("*/", self.at + 2)
                if end < 0:
                    message = "unclosed comment"
                    raise self.fail(message)
                self.at = end + 2
            else:
                return

    def value(self) -> Node:
        self.blank()
        if self.at >= len(self.text):
            message = "value expected"
            raise self.fail(message)
        char = self.text[self.at]
        if char == "{":
            return self.object()
        if char == "[":
            return self.array()
        if char == '"':
            start = self.at
            text = self.string()
            return Node(start, self.at, text)
        match = re.compile(r"-?\d+(\.\d+)?([eE][+-]?\d+)?|true|false|null").match(
            self.text, self.at
        )
        if match is None:
            message = "value expected"
            raise self.fail(message)
        self.at = match.end()
        return Node(match.start(), match.end(), json.loads(match.group()))

    def string(self) -> str:
        match = re.compile(r'"(?:[^"\\\n]|\\.)*"').match(self.text, self.at)
        if match is None:
            message = "unterminated string"
            raise self.fail(message)
        self.at = match.end()
        value = json.loads(match.group())
        assert isinstance(value, str)
        return value

    def object(self) -> Node:
        node = Node(self.at, self.at, {})
        self.at += 1
        while True:
            self.blank()
            if self.text.startswith("}", self.at):
                self.at += 1
                node.end = self.at
                return node
            if not self.text.startswith('"', self.at):
                message = "quoted object key expected"
                raise self.fail(message)
            begin = self.at
            key = self.string()
            self.blank()
            if not self.text.startswith(":", self.at):
                message = "':' expected"
                raise self.fail(message)
            self.at += 1
            child = self.value()
            node.members.append((key, begin, child))
            node.value[key] = child.value
            self.blank()
            if self.text.startswith(",", self.at):
                self.at += 1
            elif not self.text.startswith("}", self.at):
                message = "',' or '}' expected"
                raise self.fail(message)

    def array(self) -> Node:
        node = Node(self.at, self.at, [])
        self.at += 1
        while True:
            self.blank()
            if self.text.startswith("]", self.at):
                self.at += 1
                node.end = self.at
                return node
            child = self.value()
            node.value.append(child.value)
            self.blank()
            if self.text.startswith(",", self.at):
                self.at += 1
            elif not self.text.startswith("]", self.at):
                message = "',' or ']' expected"
                raise self.fail(message)


def parse_json(text: str) -> Node:
    """Parse empty text as `{}`. Raise `ConfigError` for structural errors or a non-object root.
    Malformed strings or numbers can raise `json.JSONDecodeError`.
    """
    if not text.strip():
        return Node(0, 0, {})
    parser = _Parser(text)
    node = parser.value()
    parser.blank()
    if parser.at != len(text):
        message = "unexpected text after the top JSON value"
        raise parser.fail(message)
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
    members = node.members
    index = next(i for i, (key, _begin, _child) in enumerate(members) if key == name)
    _key, begin, child = members[index]
    if index + 1 < len(members):
        start, end = begin, members[index + 1][1]
    elif index > 0:
        start, end = members[index - 1][2].end, child.end
    else:
        start, end = node.start + 1, node.end - 1
    new = text[:start] + text[end:]
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
