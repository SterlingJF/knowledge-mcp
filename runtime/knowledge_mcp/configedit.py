"""Add and remove one server entry in a host's configuration text, leaving every other byte alone.

JSON files (comments and trailing commas allowed, as JSONC hosts accept) get the entry as the
first member of its object; TOML files get its table at the end. Each edit inserts one
contiguous piece of text, which `remove` deletes again, so a file reads byte for byte as before
once the entry leaves. When the piece was changed since, `remove` deletes the entry itself.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any


class ConfigError(ValueError):
    """The text can't be read or edited safely; the message says why."""


# --- JSON with comments ----------------------------------------------------------------------


@dataclass
class Node:
    """A JSON value and where it sits in the text."""

    start: int
    end: int
    value: Any = None
    # For objects: (key, member start, value node), in order.
    members: list[tuple[str, int, Node]] = field(default_factory=list)


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0

    def fail(self, message: str) -> ConfigError:
        line = self.text.count("\n", 0, self.at) + 1
        return ConfigError(f"line {line}: {message}")

    def blank(self) -> None:
        """Skip whitespace and comments."""
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
                    raise self.fail("unclosed comment")
                self.at = end + 2
            else:
                return

    def value(self) -> Node:
        self.blank()
        if self.at >= len(self.text):
            raise self.fail("value expected")
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
            raise self.fail("value expected")
        self.at = match.end()
        return Node(match.start(), match.end(), json.loads(match.group()))

    def string(self) -> str:
        match = re.compile(r'"(?:[^"\\\n]|\\.)*"').match(self.text, self.at)
        if match is None:
            raise self.fail("unterminated string")
        self.at = match.end()
        return json.loads(match.group())

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
                raise self.fail("quoted object key expected")
            begin = self.at
            key = self.string()
            self.blank()
            if not self.text.startswith(":", self.at):
                raise self.fail("':' expected")
            self.at += 1
            child = self.value()
            node.members.append((key, begin, child))
            node.value[key] = child.value
            self.blank()
            if self.text.startswith(",", self.at):
                self.at += 1
            elif not self.text.startswith("}", self.at):
                raise self.fail("',' or '}' expected")

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
                raise self.fail("',' or ']' expected")


def parse_json(text: str) -> Node:
    """The text's top value with positions; an empty text reads as an empty object."""
    if not text.strip():
        return Node(0, 0, {})
    parser = _Parser(text)
    node = parser.value()
    parser.blank()
    if parser.at != len(text):
        raise parser.fail("unexpected text after the top JSON value")
    if not isinstance(node.value, dict):
        raise ConfigError("expected a JSON object at the top of the file")
    return node


def json_value(text: str) -> dict[str, Any]:
    return parse_json(text).value


def _child(node: Node, key: str) -> Node | None:
    for name, _begin, child in node.members:
        if name == key:
            return child
    return None


def json_entry(text: str, path: tuple[str, ...], name: str) -> Any:
    """The entry `name` in the object at `path`, or None."""
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
    return re.match(r"[ \t]*", text[line:]).group()


def _unit(text: str) -> str:
    """The file's indentation step, from its first indented line; two spaces by default."""
    match = re.search(r"\n([ \t]+)\S", text)
    return match.group(1) if match else "  "


def json_insert(
    text: str, path: tuple[str, ...], name: str, entry: Any
) -> tuple[str, str]:
    """Add `name: entry` to the object at `path`, creating missing objects.

    The entry becomes the object's first member. Returns the new text and the inserted piece.
    """
    if not text.strip():
        value: Any = {name: entry}
        for key in reversed(path):
            value = {key: value}
        piece = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        return text + piece, piece
    root = parse_json(text)
    unit = _unit(text)
    node = root
    missing: list[str] = []
    for index, key in enumerate(path):
        child = _child(node, key)
        if child is None:
            missing = list(path[index:])
            break
        if not isinstance(child.value, dict):
            raise ConfigError(f"`{'.'.join(path[: index + 1])}` is not an object")
        node = child
    if not missing and name in node.value:
        raise ConfigError(f"an entry named {name!r} already exists")
    value: Any = {name: entry}
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
    """Delete the entry: the recorded piece when it is still there once, else the member itself."""
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
    """Whether the text holds nothing but empty objects along `path`."""
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
    return value == {}


# --- TOML ------------------------------------------------------------------------------------

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
    raise ConfigError(f"can't write {value!r} as TOML")


def toml_entry(text: str, table: str, name: str) -> Any:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(str(error)) from None
    servers = data.get(table, {})
    return servers.get(name) if isinstance(servers, dict) else None


def toml_insert(
    text: str, table: str, name: str, entry: dict[str, Any]
) -> tuple[str, str]:
    """Append `[table.name]` with the entry's keys; returns the new text and the piece."""
    if toml_entry(text, table, name) is not None:
        raise ConfigError(f"an entry named {name!r} already exists")
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
        raise ConfigError(f"invalid TOML after adding the table: {error}") from None
    return new, piece


def toml_remove(text: str, table: str, name: str, piece: str | None) -> str:
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
