# File: server/app/knowledge_model/loader.py
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from app.utilities.logging import get_app_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_app_logger("knowledge_model")

DOCUMENT_KINDS = ("universe", "guidance")


def _as_version_string(raw: object) -> str:
    """Parsed YAML floats cannot preserve trailing zeros."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, float):
        return f"{raw:g}"
    return str(raw)


@dataclass(frozen=True, slots=True)
class ElementIndex:
    element_id: str
    code: str
    cardinality: str | None
    ordering_value: str | None
    closable: bool | None
    gate: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class CompositionEntry:
    element_id: str
    mode: str
    when: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ArtifactTypeIndex:
    type_id: str
    code: str
    core: tuple[CompositionEntry, ...]
    situational: tuple[CompositionEntry, ...]
    disabled_when: dict[str, Any] | None


@dataclass(slots=True)
class UniverseIndex:
    universe_id: str
    version: str
    ordering_frame: str
    document: dict[str, Any]
    statuses: frozenset[str]
    elements_by_code: dict[str, ElementIndex] = field(default_factory=dict)
    elements_by_id: dict[str, ElementIndex] = field(default_factory=dict)
    types_by_code: dict[str, ArtifactTypeIndex] = field(default_factory=dict)

    def ordering_values_for_type(self, type_code: str) -> frozenset[str]:
        artifact_type = self.types_by_code.get(type_code)
        if artifact_type is None:
            return frozenset()
        values = {
            element.ordering_value
            for entry in artifact_type.core
            if (element := self.elements_by_id.get(entry.element_id)) is not None
            and element.ordering_value is not None
        }
        return frozenset(values)

    def summary(self) -> dict[str, Any]:
        header = dict(self.document["universe"])
        header.pop("overview", None)
        header["version"] = self.version
        return header

    def served_document(self) -> dict[str, Any]:
        served = dict(self.document)
        served["universe"] = {**self.document["universe"], "version": self.version}
        return served


@dataclass(slots=True)
class GuidanceIndex:
    guidance_id: str
    guides: str
    version: str
    document: dict[str, Any]

    def served_document(self) -> dict[str, Any]:
        served = dict(self.document)
        served["guidance"] = {**self.document["guidance"], "version": self.version}
        return served


def _entry(raw: object) -> CompositionEntry | None:
    if isinstance(raw, str):
        return CompositionEntry(element_id=raw, mode="owns", when=None)
    if isinstance(raw, dict) and "element" in raw:
        return CompositionEntry(
            element_id=str(raw["element"]),
            mode=str(raw.get("mode", "owns")),
            when=raw.get("when"),
        )
    return None


def _index_universe(document: dict[str, Any]) -> UniverseIndex:
    header = document["universe"]
    ordering_frame = str(header["ordering_frame"])
    index = UniverseIndex(
        universe_id=str(header["id"]),
        version=_as_version_string(header.get("version")),
        ordering_frame=ordering_frame,
        document=document,
        statuses=frozenset(str(value) for value in (document.get("statuses") or [])),
    )

    for raw in document.get("elements") or []:
        if not isinstance(raw, dict) or "code" not in raw:
            continue
        element = ElementIndex(
            element_id=str(raw.get("id", "")),
            code=str(raw["code"]),
            cardinality=raw.get("cardinality"),
            ordering_value=raw.get(ordering_frame),
            # `closable: false` triggers refusal (app.store.validation.validate_records).
            closable=raw.get("closable"),
            gate=raw.get("gate"),
        )
        index.elements_by_code[element.code] = element
        if element.element_id:
            index.elements_by_id[element.element_id] = element

    for raw in document.get("artifacts") or []:
        if not isinstance(raw, dict) or "code" not in raw:
            continue
        composition = raw.get("composition") or {}
        core = tuple(
            entry
            for candidate in (composition.get("core") or [])
            if (entry := _entry(candidate)) is not None
        )
        situational = tuple(
            entry
            for candidate in (composition.get("situational") or [])
            if (entry := _entry(candidate)) is not None
        )
        artifact_type = ArtifactTypeIndex(
            type_id=str(raw.get("id", "")),
            code=str(raw["code"]),
            core=core,
            situational=situational,
            disabled_when=raw.get("disabled_when"),
        )
        index.types_by_code[artifact_type.code] = artifact_type

    return index


def _read_documents(directory: Path) -> list[tuple[str, str, dict[str, Any]]]:
    documents: list[tuple[str, str, dict[str, Any]]] = []
    for path in sorted(glob.glob(os.path.join(str(directory), "*.kbp.yaml"))):
        with open(path, encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
        name = os.path.basename(path)
        if not isinstance(document, dict):
            logger.warning("Skipping non-mapping document", file=name)
            continue
        kind = next((key for key in DOCUMENT_KINDS if key in document), None)
        if kind is None:
            logger.warning("Skipping document with no known header key", file=name)
            continue
        documents.append((name, kind, document))
    return documents


class KnowledgeModel:
    def __init__(
        self,
        universes: dict[str, UniverseIndex],
        guidance: dict[str, GuidanceIndex],
        source: Path,
    ) -> None:
        self.universes = universes
        self.guidance = guidance
        self.source = source

    @classmethod
    def load(cls, directory: Path) -> KnowledgeModel:
        universes: dict[str, UniverseIndex] = {}
        guidance: dict[str, GuidanceIndex] = {}
        documents = _read_documents(directory)

        for name, kind, document in documents:
            if kind != "universe":
                continue
            index = _index_universe(document)
            if index.universe_id in universes:
                logger.warning(
                    "Duplicate universe id; the later document wins",
                    universe=index.universe_id,
                    file=name,
                )
            universes[index.universe_id] = index

        for name, kind, document in documents:
            if kind != "guidance":
                continue
            header = document["guidance"]
            index = GuidanceIndex(
                guidance_id=str(header["id"]),
                guides=str(header["guides"]),
                version=_as_version_string(header.get("version")),
                document=document,
            )
            if index.guides not in universes:
                logger.warning(
                    "Guidance guides a universe this image does not carry",
                    guidance=index.guidance_id,
                    guides=index.guides,
                    file=name,
                )
            guidance[index.guides] = index

        model = cls(universes=universes, guidance=guidance, source=directory)
        for universe in universes.values():
            logger.info(
                "Universe loaded",
                universe=universe.universe_id,
                version=universe.version,
                elements=len(universe.elements_by_code),
                artifact_types=len(universe.types_by_code),
                statuses=len(universe.statuses),
                guidance=universe.universe_id in guidance,
            )
        if not universes:
            logger.error("No universe documents found", directory=str(directory))
        return model

    def universe(self, universe_id: str) -> UniverseIndex | None:
        return self.universes.get(universe_id)

    def summaries(self) -> list[dict[str, Any]]:
        return [
            universe.summary()
            for universe in sorted(
                self.universes.values(), key=lambda item: item.universe_id
            )
        ]
