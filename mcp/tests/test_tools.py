# File: mcp/tests/test_tools.py
from __future__ import annotations

import pytest

from app.errors import KmApiError
from app.settings import AGENT_PARTY
from tests.conftest import DECISION, DECISION_RECORD, UNIVERSE_ID, UNIVERSE_VERSION


def _record(**overrides):
    record = {
        'element': DECISION,
        'value': 'Store artifacts as files.',
        'asserted_by': AGENT_PARTY,
        'status': 'conjecture',
    }
    record.update(overrides)
    return record


class TestPaths:
    def test_every_artifact_path_is_flat(self, tools, seam):
        calls = seam([], {'id': 'a'}, {'id': 'a'}, {'id': 'a'}, None)

        tools['km_list_artifacts']()
        tools['km_read_artifact']('a')
        tools['km_create_artifact'](
            universe_id=UNIVERSE_ID,
            universe_version=UNIVERSE_VERSION,
            artifact_type=DECISION_RECORD,
            name='A decision record about files',
            path='Efforts/a-decision-record-about-files.md',
        )
        tools['km_update_artifact']('a', '"etag"', name='A renamed decision record')
        tools['km_delete_artifact']('a')

        for call in calls.calls:
            assert '/projects/' not in call['path'], (
                f'{call["path"]} nests under a project. v1 addresses artifacts flatly, because '
                f'an artifact may sit at the workspace level and a path cannot say "no project".'
            )

    def test_a_project_is_a_filter_rather_than_a_location(self, tools, seam):
        calls = seam([])

        tools['km_list_artifacts'](project_id='effort-1')

        assert calls.calls[0]['path'] == '/artifacts'
        assert calls.calls[0]['params']['projectId'] == 'effort-1'

    def test_a_filter_that_was_not_given_is_left_empty(self, tools, seam):
        calls = seam([])

        tools['km_list_artifacts'](status='DRAFT')

        params = calls.calls[0]['params']
        assert params['status'] == 'DRAFT'
        assert params['projectId'] is None
        assert params['artifactType'] is None
        assert params['orderingFrameValue'] is None

    def test_type_authority_comes_from_the_universe_endpoints(self, tools, seam):
        calls = seam([], {}, {})

        tools['km_list_universes']()
        tools['km_read_universe'](UNIVERSE_ID)
        tools['km_read_universe_guidance'](UNIVERSE_ID)

        assert [call['path'] for call in calls.calls] == [
            '/universes',
            f'/universes/{UNIVERSE_ID}',
            f'/universes/{UNIVERSE_ID}/guidance',
        ]


class TestWrites:
    def test_a_created_artifact_carries_the_universe_and_type_it_was_given(
        self, tools, seam
    ):
        calls = seam({'id': 'a'})

        tools['km_create_artifact'](
            universe_id=UNIVERSE_ID,
            universe_version=UNIVERSE_VERSION,
            artifact_type=DECISION_RECORD,
            name='A decision record about files',
            path='Efforts/a-decision-record-about-files.md',
            data={DECISION: [_record()]},
        )

        body = calls.calls[0]['json']
        assert body['universe'] == {'id': UNIVERSE_ID, 'version': UNIVERSE_VERSION}
        assert body['artifactType'] == DECISION_RECORD
        assert body['data'][DECISION][0]['asserted_by'] == AGENT_PARTY

    def test_a_write_never_sends_a_party_the_server_chose(self, tools, seam):
        calls = seam({'id': 'a'})
        someone_else = 'local-principal:maria'

        tools['km_create_artifact'](
            universe_id=UNIVERSE_ID,
            universe_version=UNIVERSE_VERSION,
            artifact_type=DECISION_RECORD,
            name='A decision record about files',
            path='Efforts/a-decision-record-about-files.md',
            data={DECISION: [_record(asserted_by=someone_else)]},
        )

        assert (
            calls.calls[0]['json']['data'][DECISION][0]['asserted_by'] == someone_else
        )

    def test_a_payload_the_contract_rejects_is_caught_before_it_is_sent(
        self, tools, seam
    ):
        calls = seam({'id': 'a'})

        with pytest.raises(ValueError, match='does not match the contract'):
            tools['km_create_artifact'](
                universe_id=UNIVERSE_ID,
                universe_version=UNIVERSE_VERSION,
                artifact_type=DECISION_RECORD,
                name='too short',  # the contract requires at least ten characters
                path='Efforts/too-short.md',
            )

        assert calls.calls == []

    def test_an_update_that_changes_nothing_is_refused_here(self, tools, seam):
        calls = seam({'id': 'a'})

        with pytest.raises(ValueError, match='must change something'):
            tools['km_update_artifact']('a', '"etag"')

        assert calls.calls == []

    def test_an_update_replaces_per_element_code(self, tools, seam):
        calls = seam({'id': 'a'})

        tools['km_update_artifact'](
            'a', '"etag"', data_to_update={DECISION: [_record()]}
        )

        assert calls.calls[0]['method'] == 'PUT'
        assert calls.calls[0]['headers'] == {'If-Match': '"etag"'}
        assert list(calls.calls[0]['json']['dataToUpdate']) == [DECISION]

    def test_an_artifact_read_returns_its_etag(self, tools, seam):
        seam({'id': 'a'})

        result = tools['km_read_artifact']('a')

        assert result['etag'] == '"etag"'


class TestTheCommitGate:
    def test_a_refused_commit_is_reported_rather_than_raised(self, tools, seam):
        seam(
            KmApiError(
                'An agent drafts to a reviewable state; a person commits.',
                status=403,
                error_code='FORBIDDEN',
            )
        )

        result = tools['km_commit_artifact']('a', vault='abcd1234abcd1234')

        assert result['committed'] is False
        assert result['needsPerson'] is True
        assert 'person' in result['whatToDo'].lower()
        assert 'app' not in result['whatToDo'].lower()
        assert result['personRequest'] == {
            'method': 'POST',
            'path': '/api/v1/artifacts/a/status',
            'vault': 'abcd1234abcd1234',
            'body': {'status': 'COMMITTED'},
        }

    def test_a_refused_commit_is_not_retried(self, tools, seam):
        calls = seam(KmApiError('refused', status=403, error_code='FORBIDDEN'))

        tools['km_commit_artifact']('a')

        assert len(calls.calls) == 1

    def test_a_commit_asks_the_status_route_for_committed(self, tools, seam):
        calls = seam(KmApiError('refused', status=403, error_code='FORBIDDEN'))

        tools['km_commit_artifact']('a')

        assert calls.calls[0] == {
            'method': 'POST',
            'path': '/artifacts/a/status',
            'params': None,
            'json': {'status': 'COMMITTED'},
            'vault': None,
            'headers': None,
        }

    def test_a_failure_that_is_not_the_gate_still_raises(self, tools, seam):
        seam(KmApiError('no such artifact', status=404, error_code='NOT_FOUND'))

        with pytest.raises(KmApiError):
            tools['km_commit_artifact']('a')

    def test_an_allowed_commit_is_reported_as_wrong(self, tools, seam):
        seam({'id': 'a', 'status': 'COMMITTED'})

        result = tools['km_commit_artifact']('a')

        assert result['committed'] is True
        assert 'should refuse' in result['unexpected']


class TestVaultTargeting:
    def test_a_vault_argument_reaches_the_seam(self, tools, seam):
        calls = seam([])
        tools['km_list_artifacts'](vault='abcd1234abcd1234')

        assert calls.calls[0]['vault'] == 'abcd1234abcd1234'

    def test_no_vault_argument_means_the_default_vault(self, tools, seam):
        calls = seam([])
        tools['km_list_artifacts']()

        assert calls.calls[0]['vault'] is None

    def test_every_artifact_tool_accepts_a_vault(self, tools):
        import inspect

        for name in (
            'km_list_artifacts',
            'km_read_artifact',
            'km_create_artifact',
            'km_update_artifact',
            'km_delete_artifact',
            'km_commit_artifact',
        ):
            assert 'vault' in inspect.signature(tools[name]).parameters, name

    def test_list_vaults_asks_the_typed_route(self, tools, seam):
        calls = seam([[{'id': 'a', 'name': 'Notes', 'path': '/vaults/notes'}]])
        answer = tools['km_list_vaults']()

        assert calls.calls[0]['path'] == '/vaults'
        assert answer['count'] == 1


class TestFiles:
    def test_file_listing_uses_the_raw_file_route(self, tools, seam):
        calls = seam([{'path': 'Atlas/note.md'}])

        result = tools['km_list_files'](vault='abcd1234abcd1234')

        assert result['count'] == 1
        assert calls.calls[0]['path'] == '/files'
        assert calls.calls[0]['vault'] == 'abcd1234abcd1234'

    def test_file_read_uses_the_vault_relative_path(self, tools, seam):
        calls = seam({'path': 'x/source.pdf', 'content': None})

        result = tools['km_read_file']('x/source #1.pdf')

        assert result['file']['content'] is None
        assert calls.calls[0]['path'] == '/files/x/source%20%231.pdf'
