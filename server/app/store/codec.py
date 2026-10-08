# File: server/app/store/codec.py
"""Artifact identity is frontmatter `id`. Filenames are presentation."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any

import frontmatter
import yaml

HASH_ALGORITHM = "sha256"
HASH_LENGTH = 32

# Recorded artifact names contain characters Obsidian forbids in a filename.
ILLEGAL_FILENAME_CHARS = re.compile(r'[:/\\#^\[\]|?*<>"]')
WHITESPACE_RUN = re.compile(r"\s+")

RESERVED_KEY = "knowledge-mcp"
"""Reserved store metadata, empty today."""

TOP_LEVEL_KEY_ORDER = (
    "id",
    "projectId",
    "universe",
    "artifactType",
    "name",
    "status",
    "version",
    "createdBy",
    "createdAt",
    "updatedAt",
    "lastReviewedDate",
    "provenance",
)

STRING_FIELDS = ("id", "projectId", "artifactType", "name", "status", "createdBy")
DATETIME_FIELDS = ("createdAt", "updatedAt", "lastReviewedDate")
INT_FIELDS = ("version",)

INSTANCE_STRING_FIELDS = ("id", "element", "asserted_by", "status")
INSTANCE_DATETIME_FIELDS = ("observed_at",)
INSTANCE_UUID_FIELDS = ("supersedes",)


Coercion = dict[str, str]
"""One reported type repair: `{path, was, became}`."""


def _coercion(path: str, was: str, became: str) -> Coercion:
    return {"path": path, "was": was, "became": became}


def compute_etag(data: bytes) -> str:
    digest = hashlib.new(HASH_ALGORITHM, data).hexdigest()[:HASH_LENGTH]
    return f'"{HASH_ALGORITHM}-{digest}"'


def sanitise_filename(name: str, artifact_id: str) -> str:
    cleaned = ILLEGAL_FILENAME_CHARS.sub("-", name)
    cleaned = WHITESPACE_RUN.sub(" ", cleaned).strip(" .-")
    if not cleaned:
        cleaned = artifact_id
    return f"{cleaned[:80]}.md"


def _iso(value: object) -> object:
    if isinstance(value, datetime):
        rendered = value.astimezone(UTC).isoformat()
        return rendered.replace("+00:00", "Z")
    if isinstance(value, date):
        return (
            datetime(value.year, value.month, value.day, tzinfo=UTC)
            .isoformat()
            .replace("+00:00", "Z")
        )
    return value


def _coerce_scalar(
    container: dict[str, Any],
    key: str,
    path: str,
    coercions: list[Coercion],
    *,
    to_string: bool = False,
    to_datetime: bool = False,
    to_int: bool = False,
) -> None:
    if key not in container:
        return
    value = container[key]
    if value is None:
        return

    if to_datetime and isinstance(value, (date, datetime)):
        container[key] = _iso(value)
        if not isinstance(value, str):
            coercions.append(_coercion(path, type(value).__name__, "string"))
        return

    if to_int:
        if isinstance(value, bool) or not isinstance(value, int):
            try:
                container[key] = int(value)
            except TypeError, ValueError:
                return
            coercions.append(_coercion(path, type(value).__name__, "integer"))
        return

    if to_string and not isinstance(value, str):
        container[key] = (
            _iso(value) if isinstance(value, (date, datetime)) else str(value)
        )
        coercions.append(_coercion(path, type(value).__name__, "string"))


def _coerce_records(data: object, coercions: list[Coercion]) -> None:
    """Leave `value` untouched as arbitrary JSON."""
    if not isinstance(data, dict):
        return
    for code, records in data.items():
        if not isinstance(records, list):
            continue
        for position, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            stem = f"data.{code}[{position}]"
            for key in INSTANCE_STRING_FIELDS:
                _coerce_scalar(record, key, f"{stem}.{key}", coercions, to_string=True)
            for key in INSTANCE_DATETIME_FIELDS:
                _coerce_scalar(
                    record, key, f"{stem}.{key}", coercions, to_datetime=True
                )
            for key in INSTANCE_UUID_FIELDS:
                _coerce_scalar(record, key, f"{stem}.{key}", coercions, to_string=True)


def _coerce_links(links: object, coercions: list[Coercion]) -> None:
    if not isinstance(links, dict):
        return
    for code, refs in links.items():
        if not isinstance(refs, list):
            continue
        for position, ref in enumerate(refs):
            if not isinstance(ref, dict):
                continue
            stem = f"links.{code}[{position}]"
            _coerce_scalar(
                ref, "artifactId", f"{stem}.artifactId", coercions, to_string=True
            )
            _coerce_scalar(
                ref, "instanceId", f"{stem}.instanceId", coercions, to_string=True
            )


def coerce_top_level(meta: dict[str, Any]) -> list[Coercion]:
    coercions: list[Coercion] = []

    for key in STRING_FIELDS:
        _coerce_scalar(meta, key, key, coercions, to_string=True)
    for key in DATETIME_FIELDS:
        _coerce_scalar(meta, key, key, coercions, to_datetime=True)
    for key in INT_FIELDS:
        _coerce_scalar(meta, key, key, coercions, to_int=True)

    universe = meta.get("universe")
    if isinstance(universe, dict):
        _coerce_scalar(universe, "id", "universe.id", coercions, to_string=True)
        # YAML float parsing loses trailing-zero distinctions.
        _coerce_scalar(
            universe, "version", "universe.version", coercions, to_string=True
        )

    _coerce_records(meta.get("data"), coercions)
    _coerce_links(meta.get("links"), coercions)

    return coercions


def _is_liftable(records: list[Any]) -> str | None:
    superseded = {
        record.get("supersedes")
        for record in records
        if isinstance(record, dict) and record.get("supersedes")
    }
    live = [
        record
        for record in records
        if isinstance(record, dict) and record.get("id") not in superseded
    ]
    if len(live) != 1:
        return None
    value = live[0].get("value")
    if not isinstance(value, str) or not value:
        return None
    if value != value.strip():
        return None
    return value


def _dump(post: frontmatter.Post) -> bytes:
    rendered = frontmatter.dumps(
        post,
        handler=frontmatter.YAMLHandler(),
        sort_keys=False,
        width=100000,
        allow_unicode=True,
        default_flow_style=False,
    )
    return rendered.encode("utf-8")


def _lift_prose(data: dict[str, list[Any]], headings: dict[str, str]) -> dict[str, str]:
    lifted: dict[str, str] = {}
    for code, records in data.items():
        if code not in headings:
            continue
        value = _is_liftable(records)
        if value is None:
            continue
        lifted[code] = value

        data[code] = [dict(record) for record in records]
        for record in data[code]:
            if record.get("value") == value:
                record["value"] = None
                record["valueInBody"] = True
                break
    return lifted


def to_bytes(
    artifact: dict[str, Any], prose_keys: dict[str, str] | None = None
) -> bytes:
    meta: dict[str, Any] = {}
    for key in TOP_LEVEL_KEY_ORDER:
        if key in artifact:
            meta[key] = artifact[key]

    meta["tags"] = [
        "knowledge-mcp/artifact",
        f"knowledge-mcp/{artifact.get('artifactType', 'unknown')}",
    ]

    data = {
        code: list(records) for code, records in (artifact.get("data") or {}).items()
    }
    links = {code: list(refs) for code, refs in (artifact.get("links") or {}).items()}

    headings = dict(prose_keys or {})
    lifted = _lift_prose(data, headings)

    meta["data"] = data
    meta["links"] = links
    if lifted:
        meta["proseKeys"] = {code: headings[code] for code in lifted}

    body_parts = [f"# {artifact.get('name', '')}".rstrip()]
    for code, value in lifted.items():
        body_parts.extend(["", f"## {headings[code]}", "", value.rstrip()])

    post = frontmatter.Post("\n".join(body_parts) + "\n", **meta)
    return _dump(post)


def _body_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    heading: str | None = None
    buffer: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if heading is not None:
                sections[heading] = "\n".join(buffer).strip("\n")
            heading = line[3:].strip()
            buffer = []
        elif heading is not None:
            buffer.append(line)
    if heading is not None:
        sections[heading] = "\n".join(buffer).strip("\n")
    return sections


def from_bytes(raw: bytes) -> tuple[dict[str, Any], dict[str, str], list[Coercion]]:
    post = frontmatter.loads(raw.decode("utf-8"))
    meta: dict[str, Any] = dict(post.metadata)

    prose_keys_raw = meta.pop("proseKeys", None)
    prose_keys: dict[str, str] = {}
    if isinstance(prose_keys_raw, dict):
        prose_keys = {
            str(code): str(heading) for code, heading in prose_keys_raw.items()
        }
    meta.pop("tags", None)
    meta.pop(RESERVED_KEY, None)

    coercions = coerce_top_level(meta)

    sections = _body_sections(post.content)
    data = meta.get("data")
    if isinstance(data, dict):
        for code, heading in prose_keys.items():
            records = data.get(code)
            if not isinstance(records, list):
                continue
            for record in records:
                if isinstance(record, dict) and record.pop("valueInBody", False):
                    record["value"] = sections.get(heading, "")

    meta.setdefault("data", {})
    meta.setdefault("links", {})
    return meta, prose_keys, coercions


def yaml_safe(value: object) -> object:
    return yaml.safe_load(yaml.safe_dump(value, sort_keys=False, allow_unicode=True))
