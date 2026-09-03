# File: server/app/store/validation.py
"""Five record faults are refused. Artifact findings are reported."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.errors import (
    DuplicateLiveInstanceError,
    ExhaustiveOnUnclosableError,
    UndeclaredStatusError,
    UnknownUniverseError,
    UnresolvedElementError,
    UnresolvedSupersedesError,
)

if TYPE_CHECKING:
    from app.knowledge_model import KnowledgeModel, UniverseIndex
    from app.store.file_store import StoredArtifact

# Report-only finding kinds.
COMPOSITION_CORE_MISSING = 'composition-core-missing'
COMPOSITION_MODE = 'composition-mode'
COMPOSITION_UNDECLARED_ELEMENT = 'composition-undeclared-element'
GATE_UNEVALUATED = 'gate-unevaluated'
OWNERSHIP_SHARED = 'ownership-shared'
DANGLING_LINK = 'dangling-link'
HISTORY_DROPPED = 'history-dropped'
UNIVERSE_VERSION = 'universe-version'
COERCED = 'coerced'

SEVERITY_INFO = 'info'
SEVERITY_WARNING = 'warning'


@dataclass(frozen=True, slots=True)
class Finding:
    kind: str
    severity: str
    message: str
    element: str | None = None
    instanceId: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'kind': self.kind,
            'severity': self.severity,
            'message': self.message,
            'element': self.element,
            'instanceId': self.instanceId,
        }


def _live_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    superseded = {
        record.get('supersedes') for record in records if record.get('supersedes')
    }
    return [record for record in records if record.get('id') not in superseded]


def resolve_universe(model: KnowledgeModel, reference: dict[str, Any]) -> UniverseIndex:
    """Universe version mismatch does not block resolution."""
    universe_id = str(reference.get('id', ''))
    universe = model.universe(universe_id)
    if universe is None:
        msg = f'This image carries no universe with id {universe_id!r}'
        raise UnknownUniverseError(
            msg,
            fields={'universe.id': universe_id},
        )
    return universe


def validate_records(
    data: dict[str, list[dict[str, Any]]],
    universe: UniverseIndex,
) -> None:
    for code, records in data.items():
        element = universe.elements_by_code.get(code)
        if element is None:
            msg = (
                f'Element code {code!r} does not resolve in universe '
                f'{universe.universe_id} {universe.version}'
            )
            raise UnresolvedElementError(
                msg,
                fields={'data': code},
            )

        ids_in_element = {str(record['id']) for record in records if record.get('id')}
        triples: set[tuple[str, str, str]] = set()

        for record in records:
            status = str(record.get('status', ''))
            if status not in universe.statuses:
                msg = f'Universe {universe.universe_id} does not declare status {status!r}'
                raise UndeclaredStatusError(
                    msg,
                    fields={f'data.{code}.status': status},
                )

            if record.get('exhaustive') is True and element.closable is False:
                msg = (
                    f'Element {code!r} is declared closable: false, so a set of its instances '
                    f'cannot be exhaustive'
                )
                raise ExhaustiveOnUnclosableError(
                    msg,
                    fields={f'data.{code}.exhaustive': 'true'},
                )

            supersedes = record.get('supersedes')
            if supersedes and str(supersedes) not in ids_in_element:
                msg = (
                    f'supersedes {supersedes!r} names no record of element {code!r} in this '
                    f'artifact'
                )
                raise UnresolvedSupersedesError(
                    msg,
                    fields={f'data.{code}.supersedes': str(supersedes)},
                )

        for record in _live_records(records):
            triple = (
                code,
                str(record.get('status', '')),
                str(record.get('asserted_by', '')),
            )
            if triple in triples:
                msg = (
                    'More than one un-superseded record for '
                    f'[{triple[0]}, {triple[1]}, {triple[2]}]; correct the earlier one by '
                    'naming it in supersedes'
                )
                raise DuplicateLiveInstanceError(
                    msg,
                    fields={f'data.{code}': f'{triple[1]}/{triple[2]}'},
                )
            triples.add(triple)


def _composition_findings(
    artifact: dict[str, Any],
    universe: UniverseIndex,
) -> list[Finding]:
    type_code = str(artifact.get('artifactType', ''))
    artifact_type = universe.types_by_code.get(type_code)
    if artifact_type is None:
        return [
            Finding(
                kind=COMPOSITION_UNDECLARED_ELEMENT,
                severity=SEVERITY_WARNING,
                message=(
                    f'Artifact type {type_code!r} does not resolve in universe '
                    f'{universe.universe_id} {universe.version}, so composition cannot be checked'
                ),
            )
        ]

    findings: list[Finding] = []
    data = artifact.get('data') or {}
    links = artifact.get('links') or {}

    gated = 0
    for entry in artifact_type.core:
        element = universe.elements_by_id.get(entry.element_id)
        if element is None:
            continue
        answered = bool(data.get(element.code)) or bool(links.get(element.code))
        if answered:
            if entry.mode == 'links' and data.get(element.code):
                findings.append(
                    Finding(
                        kind=COMPOSITION_MODE,
                        severity=SEVERITY_INFO,
                        message=(
                            f'This type links {entry.element_id!r} rather than owning it; this '
                            f'artifact holds an instance of it'
                        ),
                        element=element.code,
                    )
                )
            continue
        if entry.when or element.gate:
            gated += 1
            continue
        findings.append(
            Finding(
                kind=COMPOSITION_CORE_MISSING,
                severity=SEVERITY_INFO,
                message=f'Core element {entry.element_id!r} has no instance and no link yet',
                element=element.code,
            )
        )

    if gated:
        # Scope frame values are unresolved at MVP. Report gates as unevaluated.
        findings.append(
            Finding(
                kind=GATE_UNEVALUATED,
                severity=SEVERITY_INFO,
                message=(
                    f'{gated} core element(s) are behind a frame condition this image cannot '
                    f'evaluate, because nothing resolves frame values at the local end yet'
                ),
            )
        )

    return findings


def _link_findings(
    artifact: dict[str, Any],
    others: list[StoredArtifact],
) -> list[Finding]:
    findings: list[Finding] = []
    links = artifact.get('links') or {}
    if not links:
        return findings

    by_artifact = {str(stored.artifact['id']): stored for stored in others}
    for code, references in links.items():
        for reference in references or []:
            target_id = str(reference.get('artifactId', ''))
            instance_id = str(reference.get('instanceId', ''))
            target = by_artifact.get(target_id)
            if target is None:
                findings.append(
                    Finding(
                        kind=DANGLING_LINK,
                        severity=SEVERITY_INFO,
                        message=f'Link points at artifact {target_id}, which is not in this store',
                        element=code,
                        instanceId=instance_id,
                    )
                )
                continue
            target_ids = {
                str(record.get('id'))
                for records in (target.artifact.get('data') or {}).values()
                for record in records or []
            }
            if instance_id not in target_ids:
                findings.append(
                    Finding(
                        kind=DANGLING_LINK,
                        severity=SEVERITY_INFO,
                        message=(
                            f'Link points at instance {instance_id}, which artifact {target_id} '
                            f'does not hold'
                        ),
                        element=code,
                        instanceId=instance_id,
                    )
                )
    return findings


def _ownership_findings(
    artifact: dict[str, Any],
    others: list[StoredArtifact],
) -> list[Finding]:
    artifact_id = str(artifact.get('id', ''))
    mine = {
        str(record.get('id')): code
        for code, records in (artifact.get('data') or {}).items()
        for record in records or []
        if record.get('id')
    }
    if not mine:
        return []

    findings: list[Finding] = []
    for stored in others:
        if str(stored.artifact['id']) == artifact_id:
            continue
        for code, records in (stored.artifact.get('data') or {}).items():
            for record in records or []:
                instance_id = str(record.get('id', ''))
                if instance_id in mine:
                    findings.append(
                        Finding(
                            kind=OWNERSHIP_SHARED,
                            severity=SEVERITY_WARNING,
                            message=(
                                f'Instance {instance_id} is also held by artifact '
                                f'{stored.artifact["id"]}; exactly one artifact should own it '
                                f'and the other should link'
                            ),
                            element=code,
                            instanceId=instance_id,
                        )
                    )
    return findings


def build_report(
    artifact: dict[str, Any],
    universe: UniverseIndex,
    others: list[StoredArtifact],
    coercions: list[dict[str, str]] | None = None,
    extra: list[Finding] | None = None,
) -> dict[str, Any]:
    findings: list[Finding] = []

    pinned = str((artifact.get('universe') or {}).get('version', ''))
    if pinned and pinned != universe.version:
        findings.append(
            Finding(
                kind=UNIVERSE_VERSION,
                severity=SEVERITY_WARNING,
                message=(
                    f'This artifact pins {universe.universe_id} {pinned}; this image carries '
                    f'{universe.version}. Codes were resolved against the image copy'
                ),
            )
        )

    findings.extend(_composition_findings(artifact, universe))
    findings.extend(_link_findings(artifact, others))
    findings.extend(_ownership_findings(artifact, others))
    findings.extend(extra or [])

    findings.extend(
        Finding(
            kind=COERCED,
            severity=SEVERITY_WARNING,
            message=(
                f'{coercion["path"]} was read as {coercion["was"]} and re-imposed as '
                f'{coercion["became"]}; quote the value in the file to keep it stable'
            ),
        )
        for coercion in coercions or []
    )

    return {'findings': [finding.as_dict() for finding in findings]}


def dropped_history_findings(
    previous: dict[str, list[dict[str, Any]]],
    incoming: dict[str, list[dict[str, Any]]],
) -> list[Finding]:
    findings: list[Finding] = []
    for code, records in incoming.items():
        before = {
            str(record.get('id'))
            for record in previous.get(code, [])
            if record.get('id')
        }
        after = {str(record.get('id')) for record in records or [] if record.get('id')}
        lost = before - after
        if lost:
            findings.append(
                Finding(
                    kind=HISTORY_DROPPED,
                    severity=SEVERITY_WARNING,
                    message=(
                        f'{len(lost)} record(s) previously held under {code} are not in this '
                        f'update and are gone; per-code replacement replaces the whole list'
                    ),
                    element=code,
                )
            )
    return findings
