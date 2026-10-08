# File: server/app/store/service.py
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from app.errors import ForbiddenError, NotFoundError
from app.store import validation

if TYPE_CHECKING:
    from app.context import RequestContext
    from app.knowledge_model import KnowledgeModel
    from app.store.file_store import FileStore, StoredArtifact
    from app.store.validation import Finding

DEFAULT_EXHAUSTIVE = "unknown"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return str(uuid.uuid4())


def _summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: artifact.get(key)
        for key in (
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
        )
    }


def _prepare_records(
    data: dict[str, list[dict[str, Any]]] | None,
    *,
    stamped_at: str,
    existing: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Preserve ids already held under same code. Mint all others."""
    prepared: dict[str, list[dict[str, Any]]] = {}
    for code, records in (data or {}).items():
        held = {
            str(record["id"])
            for record in (existing or {}).get(code, [])
            if record.get("id")
        }
        prepared[code] = [
            {
                "id": (
                    str(record["id"])
                    if record.get("id") and str(record["id"]) in held
                    else _new_id()
                ),
                "element": record.get("element", code),
                "value": record.get("value"),
                "asserted_by": record.get("asserted_by"),
                "binding_on": list(record.get("binding_on") or []),
                "status": record.get("status"),
                "observed_at": record.get("observed_at") or stamped_at,
                "supersedes": record.get("supersedes"),
                "exhaustive": record.get("exhaustive", DEFAULT_EXHAUSTIVE),
            }
            for record in (records or [])
        ]
    return prepared


def _guard_agent_assertions(
    data: dict[str, list[dict[str, Any]]],
    context: RequestContext,
) -> None:
    """An agent may only assert as itself. Gate 1's second rule."""
    if not context.is_agent:
        return
    for code, records in data.items():
        for record in records:
            asserted_by = str(record.get("asserted_by", ""))
            if asserted_by != context.actor:
                msg = (
                    f"{context.actor} may not assert on behalf of {asserted_by!r}. An agent "
                    f"drafts as itself; a person commits as themselves"
                )
                raise ForbiddenError(
                    msg,
                    fields={f"data.{code}.asserted_by": asserted_by},
                )


class ArtifactService:
    def __init__(self, store: FileStore, model: KnowledgeModel) -> None:
        self.store = store
        self.model = model

    def _report_for(
        self,
        artifact: dict[str, Any],
        others: list[StoredArtifact],
        coercions: list[dict[str, str]] | None = None,
        extra: list[Finding] | None = None,
    ) -> dict[str, Any]:
        universe = validation.resolve_universe(
            self.model, artifact.get("universe") or {}
        )
        return validation.build_report(artifact, universe, others, coercions, extra)

    def _served(
        self,
        stored: StoredArtifact,
        others: list[StoredArtifact],
        extra: list[Finding] | None = None,
    ) -> dict[str, Any]:
        artifact = dict(stored.artifact)
        artifact["report"] = self._report_for(artifact, others, stored.coercions, extra)
        return artifact

    def list_summaries(
        self,
        project_id: str | None = None,
        artifact_type: str | None = None,
        status: str | None = None,
        ordering_frame_value: str | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for stored in self.store.scan():
            artifact = stored.artifact
            if (
                project_id is not None
                and str(artifact.get("projectId") or "") != project_id
            ):
                continue
            if (
                artifact_type is not None
                and str(artifact.get("artifactType")) != artifact_type
            ):
                continue
            if status is not None and str(artifact.get("status")) != status:
                continue
            if ordering_frame_value is not None and not self._matches_ordering_value(
                artifact, ordering_frame_value
            ):
                continue
            results.append(_summary(artifact))
        results.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
        return results

    def _matches_ordering_value(self, artifact: dict[str, Any], value: str) -> bool:
        universe = self.model.universe(
            str((artifact.get("universe") or {}).get("id", ""))
        )
        if universe is None:
            return False
        return value in universe.ordering_values_for_type(
            str(artifact.get("artifactType", ""))
        )

    def get(self, artifact_id: str) -> tuple[dict[str, Any], str]:
        others = self.store.scan()
        for stored in others:
            if str(stored.artifact["id"]) == artifact_id:
                return self._served(stored, others), stored.etag
        msg = f"No artifact with id {artifact_id}"
        raise NotFoundError(msg)

    def create(
        self,
        payload: dict[str, Any],
        context: RequestContext,
        prose_keys: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        stamped_at = _now()
        universe_ref = dict(payload["universe"])
        universe = validation.resolve_universe(self.model, universe_ref)

        data = _prepare_records(payload.get("data"), stamped_at=stamped_at)
        _guard_agent_assertions(data, context)
        validation.validate_records(data, universe)

        artifact: dict[str, Any] = {
            "id": _new_id(),
            "projectId": payload.get("projectId"),
            "universe": universe_ref,
            "artifactType": payload["artifactType"],
            "name": payload["name"],
            # Committing is a separate operation.
            "status": "DRAFT",
            "version": 1,
            # Server-stamped. Payload models forbid these fields (server/app/api_models_auto.py).
            "createdBy": context.party,
            "createdAt": stamped_at,
            "updatedAt": stamped_at,
            "lastReviewedDate": payload.get("lastReviewedDate"),
            "provenance": payload.get("provenance") or {"contextArtifactIds": []},
            "data": data,
            "links": payload.get("links") or {},
        }

        path = self.store.resolve_new(str(payload["path"]))
        stored = self.store.write(artifact, prose_keys or {}, path)
        others = self.store.scan()
        return self._served(stored, others), stored.etag

    def update(
        self,
        artifact_id: str,
        payload: dict[str, Any],
        context: RequestContext,
        expected_etag: str,
        prose_keys: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], str]:
        current = self.store.get(artifact_id)
        artifact = dict(current.artifact)
        universe = validation.resolve_universe(
            self.model, artifact.get("universe") or {}
        )
        stamped_at = _now()

        extra: list[Finding] = []

        if "name" in payload and payload["name"] is not None:
            artifact["name"] = payload["name"]
        if "lastReviewedDate" in payload:
            artifact["lastReviewedDate"] = payload["lastReviewedDate"]
        if payload.get("provenance") is not None:
            artifact["provenance"] = payload["provenance"]

        if payload.get("dataToUpdate") is not None:
            incoming = _prepare_records(
                payload["dataToUpdate"],
                stamped_at=stamped_at,
                existing=artifact.get("data") or {},
            )
            _guard_agent_assertions(incoming, context)
            merged = dict(artifact.get("data") or {})
            extra.extend(
                validation.dropped_history_findings(
                    artifact.get("data") or {}, incoming
                )
            )
            for code, records in incoming.items():
                if records:
                    merged[code] = records
                else:
                    merged.pop(code, None)
            validation.validate_records(merged, universe)
            artifact["data"] = merged

        if payload.get("linksToUpdate") is not None:
            merged_links = dict(artifact.get("links") or {})
            for code, references in payload["linksToUpdate"].items():
                if references:
                    merged_links[code] = references
                else:
                    merged_links.pop(code, None)
            artifact["links"] = merged_links

        artifact["version"] = int(artifact.get("version", 1)) + 1
        artifact["updatedAt"] = stamped_at

        keys = dict(current.prose_keys)
        keys.update(prose_keys or {})
        stored = self.store.write(
            artifact, keys, current.path, expected_etag=expected_etag
        )
        others = self.store.scan()
        return self._served(stored, others, extra), stored.etag

    def transition_status(
        self,
        artifact_id: str,
        status: str,
        context: RequestContext,
    ) -> tuple[dict[str, Any], str]:
        """Gate 1 person-only status transition."""
        if context.is_agent:
            msg = (
                "An agent drafts to a reviewable state; a person commits. This operation is "
                "the commitment, and it is not an agent's to make"
            )
            raise ForbiddenError(
                msg,
                fields={"status": status},
            )

        current = self.store.get(artifact_id)
        artifact = dict(current.artifact)
        artifact["status"] = status
        artifact["version"] = int(artifact.get("version", 1)) + 1
        artifact["updatedAt"] = _now()

        stored = self.store.write(
            artifact, current.prose_keys, current.path, expected_etag=current.etag
        )
        others = self.store.scan()
        return self._served(stored, others), stored.etag

    def delete(self, artifact_id: str) -> None:
        """Inbound links remain. Validation reports them as `dangling-link` (app.store.validation._link_findings)."""
        current = self.store.get(artifact_id)
        self.store.delete(current.path)
