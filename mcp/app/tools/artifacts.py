# File: mcp/app/tools/artifacts.py

from __future__ import annotations

from typing import Any

from mcp.types import ToolAnnotations
from pydantic import ValidationError

from app import km_api
from app.api_models_auto import (
    ArtifactCreationPayload,
    ArtifactStatusEnum,
    ArtifactStatusTransitionPayload,
    ArtifactUpdatePayload,
    InstanceRecordInput,
    LinkRef,
)
from app.errors import KmApiError
from app.settings import AGENT_PARTY

_HTTP_FORBIDDEN = 403

_COMMIT_DESCRIPTION = """\
Ask for an artifact to be committed, and relay the answer.

Committing is a person's to do, and this server is an agent, so the store refuses it. That refusal
is the expected result of this call, not a failure of it: use this tool when a draft is ready, then
tell the person it is waiting for them and what it says. The result carries a request the person
can execute through any trusted local client. Calling it is the designed path.

The tool reports the refusal instead of raising, and does not retry. Nothing about the artifact
changes.\
"""

_UPDATE_DESCRIPTION = """\
Replace parts of an artifact.

Read the artifact first and pass its `etag`. The update is refused if the file changed after that
read.

`data_to_update` and `links_to_update` replace per element code: a code you send replaces that
code's whole list, a code you leave out is untouched, and an empty list clears it.

Two consequences worth knowing before you call this. A correction sends *both* records — the one
being superseded, carrying its own `id`, and the one superseding it, whose `supersedes` names that
id. And you may only replace lists whose records are all your own: sending a record asserted by the
person, even to preserve it, is refused. In practice, only rewrite element codes you asserted.\
"""


def register(mcp: Any) -> None:
    @mcp.tool(
        name='km_list_artifacts',
        description=(
            'List artifacts in the store, newest first. Filters are optional and combine. '
            'Omitting `project_id` returns every project plus artifacts that belong to none. '
            'Pass `vault` (an id from km_list_vaults) to target a vault other than the default.'
        ),
        annotations=ToolAnnotations(
            title='List artifacts',
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def list_artifacts(
        project_id: str | None = None,
        artifact_type: str | None = None,
        status: str | None = None,
        ordering_frame_value: str | None = None,
        vault: str | None = None,
    ) -> dict[str, Any]:
        payload, receipt = km_api.request(
            'GET',
            '/artifacts',
            vault=vault,
            params={
                'projectId': project_id,
                'artifactType': artifact_type,
                'status': status,
                'orderingFrameValue': ordering_frame_value,
            },
        )
        return {
            'count': len(payload or []),
            'artifacts': payload,
            '_request': receipt,
        }

    @mcp.tool(
        name='km_read_artifact',
        description=(
            'Read one artifact in full, including its instance records and any findings the '
            'store reports about it.'
        ),
        annotations=ToolAnnotations(
            title='Read an artifact',
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def read_artifact(artifact_id: str, vault: str | None = None) -> dict[str, Any]:
        payload, receipt = km_api.request(
            'GET', f'/artifacts/{artifact_id}', vault=vault
        )
        return {'artifact': payload, 'etag': receipt.get('etag'), '_request': receipt}

    @mcp.tool(
        name='km_create_artifact',
        description=(
            'Create an artifact as a draft. Every record you write must set `asserted_by` to '
            f'"{AGENT_PARTY}" — you may only assert as yourself. The artifact is created as a '
            'draft; a person commits it. Pass `vault` (an id from km_list_vaults) to target '
            'a vault other than the default.'
        ),
        annotations=ToolAnnotations(
            title='Create an artifact',
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    def create_artifact(  # noqa: PLR0913 - arity is the contract's field count
        universe_id: str,
        universe_version: str,
        artifact_type: str,
        name: str,
        path: str,
        data: dict[str, list[InstanceRecordInput]] | None = None,
        links: dict[str, list[LinkRef]] | None = None,
        project_id: str | None = None,
        context_artifact_ids: list[str] | None = None,
        vault: str | None = None,
    ) -> dict[str, Any]:
        body = _build(
            ArtifactCreationPayload,
            {
                'universe': {'id': universe_id, 'version': universe_version},
                'artifactType': artifact_type,
                'name': name,
                'path': path,
                'projectId': project_id,
                'data': _dump_data(data),
                'links': _dump_links(links),
                'provenance': _provenance(context_artifact_ids),
            },
        )
        payload, receipt = km_api.request('POST', '/artifacts', json=body, vault=vault)
        return {'artifact': payload, '_request': receipt}

    @mcp.tool(
        name='km_update_artifact',
        description=_UPDATE_DESCRIPTION,
        annotations=ToolAnnotations(
            title='Update an artifact',
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def update_artifact(
        artifact_id: str,
        etag: str,
        name: str | None = None,
        data_to_update: dict[str, list[InstanceRecordInput]] | None = None,
        links_to_update: dict[str, list[LinkRef]] | None = None,
        context_artifact_ids: list[str] | None = None,
        vault: str | None = None,
    ) -> dict[str, Any]:
        body = _build(
            ArtifactUpdatePayload,
            {
                'name': name,
                'dataToUpdate': _dump_data(data_to_update),
                'linksToUpdate': _dump_links(links_to_update),
                'provenance': _provenance(context_artifact_ids),
            },
        )
        if not body:
            msg = (
                'An update must change something. Pass at least one of name, data_to_update, '
                'links_to_update or context_artifact_ids.'
            )
            raise ValueError(msg)

        payload, receipt = km_api.request(
            'PUT',
            f'/artifacts/{artifact_id}',
            json=body,
            vault=vault,
            headers={'If-Match': etag},
        )
        return {'artifact': payload, 'etag': receipt.get('etag'), '_request': receipt}

    @mcp.tool(
        name='km_delete_artifact',
        description=(
            'Delete an artifact permanently. The file is removed and any links pointing at it '
            'are left dangling, which the store reports on the artifacts that hold them. There '
            'is no undo. Ask the person first.'
        ),
        annotations=ToolAnnotations(
            title='Delete an artifact',
            read_only_hint=False,
            destructive_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def delete_artifact(artifact_id: str, vault: str | None = None) -> dict[str, Any]:
        _, receipt = km_api.request('DELETE', f'/artifacts/{artifact_id}', vault=vault)
        return {'deleted': artifact_id, '_request': receipt}

    @mcp.tool(
        name='km_commit_artifact',
        description=_COMMIT_DESCRIPTION,
        annotations=ToolAnnotations(
            title='Ask for a commit',
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    def commit_artifact(artifact_id: str, vault: str | None = None) -> dict[str, Any]:
        body = ArtifactStatusTransitionPayload(
            status=ArtifactStatusEnum.COMMITTED
        ).model_dump(mode='json')

        try:
            payload, receipt = km_api.request(
                'POST', f'/artifacts/{artifact_id}/status', json=body, vault=vault
            )
        except KmApiError as refusal:
            if refusal.status != _HTTP_FORBIDDEN:
                raise
            return {
                'committed': False,
                'needsPerson': True,
                'artifactId': artifact_id,
                'refusal': refusal.detail,
                'personRequest': {
                    'method': 'POST',
                    'path': f'/api/v1/artifacts/{artifact_id}/status',
                    'vault': vault,
                    'body': body,
                },
                'whatToDo': (
                    'Present personRequest to the person for execution through a trusted local '
                    'client. Do not execute or retry it yourself.'
                ),
            }

        # Unreachable unless agent header is missing.
        return {
            'committed': True,
            'artifact': payload,
            'unexpected': (
                'The store allowed this server to commit, which it should refuse. The agent '
                'header is missing or malformed, so writes are being recorded as the person.'
            ),
            '_request': receipt,
        }


def _build(model: type, values: dict[str, Any]) -> dict[str, Any]:
    supplied = {key: value for key, value in values.items() if value is not None}
    try:
        return model(**supplied).model_dump(mode='json', exclude_unset=True)
    except ValidationError as error:
        msg = f'This payload does not match the contract:\n{error}'
        raise ValueError(msg) from error


def _dump_data(
    data: dict[str, list[InstanceRecordInput]] | None,
) -> dict[str, list[dict[str, Any]]] | None:
    if data is None:
        return None
    return {
        code: [
            _dump(InstanceRecordInput, record, exclude_unset=True) for record in records
        ]
        for code, records in data.items()
    }


def _dump_links(
    links: dict[str, list[LinkRef]] | None,
) -> dict[str, list[dict[str, Any]]] | None:
    if links is None:
        return None
    return {
        code: [_dump(LinkRef, link) for link in links_for_code]
        for code, links_for_code in links.items()
    }


def _dump(model: type, value: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if not isinstance(value, model):
        try:
            value = model.model_validate(value)
        except ValidationError as error:
            msg = f'This {model.__name__} does not match the contract:\n{error}'
            raise ValueError(msg) from error
    return value.model_dump(mode='json', exclude_unset=exclude_unset)


def _provenance(context_artifact_ids: list[str] | None) -> dict[str, Any] | None:
    if context_artifact_ids is None:
        return None
    return {'contextArtifactIds': context_artifact_ids}
