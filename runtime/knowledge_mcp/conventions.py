from __future__ import annotations

import posixpath
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, NoReturn

import yaml
from pydantic import BaseModel, ValidationError

from knowledge_mcp import document_types as records
from knowledge_mcp import problems, schemas
from knowledge_mcp.models import AllowedBy, KnowledgeBusFolder, ListedFile
from knowledge_mcp.models_auto.common_schema import FilingValue
from knowledge_mcp.models_auto.conventions_schema import NamingAndFilingConventions
from knowledge_mcp.models_auto.conventions_update_schema import Change
from knowledge_mcp.scope import Workspace
from knowledge_mcp.type_scope import Scopes

PLACE = ".knowledge-bus/plugins/knowledge-mcp/conventions.yaml"
SCHEMA = "knowledge-mcp/conventions/1"
UNSAFE = re.compile(r"[#|^:/\\\[\]\x00-\x1f\x7f-\x9f]|%%")
IMPLEMENTATION = {
    ".knowledge-bus",
    ".obsidian",
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def invalid(
    detail: str, pointer: str = "#/conventions", code: str = "conventions-invalid"
) -> NoReturn:
    raise problems.Error(detail, code=code, pointer=pointer)


def plain(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(mode="json", by_alias=True, exclude_none=True)


def _parts(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in entry["folder"] if isinstance(p, dict)] + [
        p for p in entry["name"]["parts"]
    ]


def _segment(text: str, pointer: str, code: str) -> str:
    if not text or text in (".", "..") or UNSAFE.search(text):
        invalid(
            "Use a nonempty path segment without traversal, separators or link-breaking characters.",
            pointer,
            code,
        )
    if text.casefold() in IMPLEMENTATION:
        invalid(
            "Choose a document folder outside configuration and implementation directories.",
            pointer,
            code,
        )
    return text


def validate_pattern(entry: dict[str, Any], pointer: str) -> None:
    uses_content = any(p["part"] == "content" for p in _parts(entry))
    if uses_content != ("content" in entry):
        invalid(
            "Define content exactly when a folder or name part uses content.", pointer
        )
    for i, part in enumerate(entry["folder"]):
        if isinstance(part, str):
            _segment(part, f"{pointer}/folder/{i}", "conventions-invalid")
    for part in _parts(entry):
        if part["part"] == "literal":
            _segment(part["value"], pointer, "conventions-invalid")


def parse(text: str) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        invalid(f"Correct the YAML in {PLACE}: {error}")
    issues = schemas.convention_issues(data)
    if issues:
        invalid(f"Correct {PLACE}: " + "; ".join(issues))
    try:
        saved = NamingAndFilingConventions.model_validate(data)
    except ValidationError as error:
        invalid(f"Correct {PLACE}: {error}")
    if saved.from_parent:
        invalid(
            "Parent conventions are reserved for a later version. Send an empty from_parent list.",
            "#/conventions/from_parent",
            "conventions-unsupported",
        )
    found = []
    seen = set()
    for i, entry in enumerate(saved.conventions):
        value = plain(entry)
        key = pair(value)
        if key in seen:
            invalid(
                "Keep one convention for each universe spec and document type.",
                f"#/conventions/conventions/{i}",
            )
        seen.add(key)
        validate_pattern(value, f"#/conventions/conventions/{i}")
        found.append(value)
    return sorted(found, key=pair)


def pair(value: dict[str, Any]) -> tuple[str, str]:
    return value["universe_spec"], value["document_type"]


def received_text(workspace: Workspace, text: str | None, digest: str | None) -> str:
    if text is not None and digest is not None:
        invalid(
            "Send conventions or conventions_digest, never both.",
            "#/conventions_digest",
            "argument-invalid",
        )
    if digest is not None:
        held = workspace.recall(digest)
        if held is None:
            invalid(
                f"Send the current text of {PLACE}; this session holds no text for the supplied digest.",
                "#/conventions_digest",
                "digest-unknown",
            )
        return held
    return text or ""


def prepare(
    workspace: Workspace,
    text: str,
    *,
    changes: list[Change],
    allowed_by: AllowedBy | None,
    folders: list[KnowledgeBusFolder],
) -> dict[str, Any]:
    current = parse(text)
    entries = {pair(e): e for e in current}
    effective = []
    seen = set()
    scopes = Scopes(workspace, folders)
    for i, operation in enumerate(changes):
        change = plain(operation)
        key = pair(change)
        pointer = problems.pointer("changes", i)
        if key in seen:
            invalid("Send one change per universe spec and document type.", pointer)
        seen.add(key)
        if change["change"] == "remove":
            if key not in entries:
                continue
            del entries[key]
        else:
            validate_pattern(change, pointer)
            kinds = scopes.kinds_at("document.md")
            if key[0] not in kinds or key[1] not in kinds[key[0]][1]:
                invalid(
                    "Choose a document type declared in the supplied root definitions or bundled universe specs.",
                    pointer + "/document_type",
                    "document-type-unknown",
                )
            pattern = {k: v for k, v in change.items() if k != "change"}
            previous = {
                k: v
                for k, v in entries.get(key, {}).items()
                if k not in ("allowed_by", "time")
            }
            if pattern == previous:
                continue
            entries[key] = {
                **pattern,
                "allowed_by": plain(allowed_by) if allowed_by else None,
                "time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        effective.append(change)
    record = None
    if effective and allowed_by is not None:
        record = yaml.safe_dump(
            {
                "schema": SCHEMA,
                "from_parent": [],
                "conventions": [entries[k] for k in sorted(entries)],
            },
            sort_keys=False,
            allow_unicode=True,
        )
        workspace.remember(record)
    return dict(
        schema="knowledge-mcp/conventions-update/1",
        file=PLACE,
        status="unchanged"
        if not effective
        else "permission_needed"
        if allowed_by is None
        else "ready",
        based_on=workspace.remember(text),
        current=current,
        changes=sorted(effective, key=pair),
        allowed_by=plain(allowed_by) if allowed_by else None,
        record=record,
        digest=records.digest(record) if record is not None else None,
        received=[
            *scopes.received.values(),
            {"name": PLACE, "digest": records.digest(text)},
        ],
    )


def _dynamic(text: str, name: dict[str, Any], pointer: str) -> str:
    text = unicodedata.normalize("NFC", text)
    if name["case"] == "lower":
        text = text.lower()
    text = UNSAFE.sub("", text)
    separator = name["separator"]
    text = re.sub(
        r"[\s" + re.escape(separator) + r"]+", lambda _: separator, text
    ).strip(separator)
    return _segment(text, pointer, "filing-values-invalid")


def _needed(
    entry: dict[str, Any], properties: dict[str, str], content: str | None
) -> list[dict[str, str]]:
    needed = []
    for part in _parts(entry):
        source = part["part"]
        if source in ("date", "property") and part["property"] not in properties:
            item = dict(source="property", name=part["property"])
        elif source == "content" and content is None:
            item = dict(source="content", name=entry["content"]["label"])
        else:
            continue
        if item not in needed:
            needed.append(item)

    return needed


def render(
    entry: dict[str, Any], value: FilingValue | None, pointer: str
) -> tuple[list[str], list[str], list[dict[str, str]]]:
    properties = (value.properties or {}) if value else {}
    content = value.content if value else None
    needed = _needed(entry, properties, content)

    def part_text(part: dict[str, Any]) -> str:
        source = part["part"]
        if source == "literal":
            return str(part["value"])
        if source == "document_type":
            return _dynamic(entry["document_type"], entry["name"], pointer)
        if source == "content":
            return (
                _dynamic(content, entry["name"], pointer + "/content")
                if content is not None
                else ""
            )
        key = part["property"]
        if key not in properties:
            return ""
        text = properties[key]
        at = pointer + "/properties/" + key.replace("~", "~0").replace("/", "~1")
        if source == "date":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                invalid(
                    "Supply a valid Gregorian date as YYYY-MM-DD.",
                    at,
                    "filing-values-invalid",
                )
            try:
                parsed = date.fromisoformat(text)
            except ValueError:
                invalid(
                    "Supply a valid Gregorian date as YYYY-MM-DD.",
                    at,
                    "filing-values-invalid",
                )
            return parsed.isoformat()[
                : {"YYYY": 4, "YYYY-MM": 7, "YYYY-MM-DD": 10}[part["format"]]
            ]
        return _dynamic(text, entry["name"], at)

    folder = [p if isinstance(p, str) else part_text(p) for p in entry["folder"]]
    name = [part_text(p) for p in entry["name"]["parts"]]
    return folder, name, needed


@dataclass
class Filing:
    definitions: dict[tuple[str, str], dict[str, Any]]
    digest: str
    values: dict[tuple[str, str, str], tuple[FilingValue, str]] = field(
        default_factory=dict
    )

    @classmethod
    def read(
        cls,
        workspace: Workspace,
        text: str | None,
        digest: str | None,
        values: list[FilingValue] | None,
    ) -> Filing:
        supplied = received_text(workspace, text, digest)
        self = cls({pair(e): e for e in parse(supplied)}, workspace.remember(supplied))
        for i, value in enumerate(values or []):
            pointer = problems.pointer("filing_values", i)
            if value.properties is None:
                invalid(
                    "Supply properties as a map of text values.",
                    pointer + "/properties",
                    "filing-values-invalid",
                )
            if "content" in value.model_fields_set and value.content is None:
                invalid(
                    "Supply content as text or omit the content value.",
                    pointer + "/content",
                    "filing-values-invalid",
                )
            path = records.normal_path(
                value.path, pointer=pointer + "/path", code="filing-values-invalid"
            )
            key = path, value.universe_spec, value.document_type
            if key in self.values:
                invalid(
                    "Supply values once per path, universe spec and document type.",
                    pointer,
                    "filing-values-invalid",
                )
            definition = self.definitions.get(key[1:])
            if definition is None:
                invalid(
                    "Supply filing values for an applicable convention.",
                    pointer,
                    "filing-values-invalid",
                )
            render(definition, value, pointer)
            self.values[key] = value, pointer
        return self

    def assess(
        self, result: dict[str, Any], listing: list[ListedFile] | None
    ) -> dict[str, Any] | None:
        entry = self.definitions.get((result["universe_spec"], result["document_type"]))
        if entry is None:
            return None
        result["convention"] = dict(
            file=PLACE, folder="", digest=self.digest, definition=entry
        )
        value, pointer = self.values.get(
            (result["path"], *pair(entry)), (None, "#/filing_values")
        )
        segments, parts, needed = render(entry, value, pointer)
        if needed:
            result.update(status="values_needed", needed=needed)
            return result
        if listing is None:
            result["status"] = "listing_needed"
            return result
        folder = "/".join(segments)
        name = (
            entry["name"]["separator"].join(parts)
            + posixpath.splitext(result["path"])[1]
        )
        _segment(name, pointer, "filing-values-invalid")
        destination = posixpath.join(folder, name)
        paths = {records.normal_path(p.path) for p in listing}
        # Case behavior is unknown for supplied inventories, so block equivalent paths.
        identities = {unicodedata.normalize("NFC", p).casefold() for p in paths}
        identity = unicodedata.normalize("NFC", destination).casefold()
        folder_identity = unicodedata.normalize("NFC", folder).casefold()
        if destination == result["path"]:
            result["status"] = "already_matches"
        elif identity in identities:
            result["status"] = "destination_occupied"
        else:
            result["status"] = "proposed"
            result["proposal"] = dict(
                folder=folder,
                name=name,
                path=destination,
                folder_new=bool(folder)
                and not any(p.startswith(folder_identity + "/") for p in identities),
                name_style="convention",
                evidence=[],
                folder_counts=[],
            )
        return result
