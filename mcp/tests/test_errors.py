# File: mcp/tests/test_errors.py
from __future__ import annotations

from app.errors import parse_error_body


class TestTheTwoShapes:
    def test_the_stores_own_refusal_keeps_its_code_and_fields(self):
        error = parse_error_body(
            403,
            {
                'detail': 'An agent drafts to a reviewable state; a person commits.',
                'errorCode': 'FORBIDDEN',
                'fields': {'status': 'COMMITTED'},
            },
        )

        assert error.status == 403
        assert error.error_code == 'FORBIDDEN'
        assert error.fields == {'status': 'COMMITTED'}
        assert 'a person commits' in error.detail

    def test_a_payload_the_models_reject_arrives_as_an_array_and_still_reads(self):
        # FastAPI validation shape: list under detail, no errorCode.
        error = parse_error_body(
            422,
            {
                'detail': [
                    {
                        'loc': ['body', 'data', 'e43c2', 0, 'asserted_by'],
                        'msg': 'Field required',
                        'type': 'missing',
                    }
                ]
            },
        )

        assert error.schema_rejection is True
        assert error.error_code is None
        assert 'body.data.e43c2.0.asserted_by' in error.detail
        assert 'Field required' in error.detail

    def test_a_body_in_neither_shape_still_produces_an_error_worth_reading(self):
        error = parse_error_body(502, '<html>gateway</html>')

        assert error.status == 502
        assert 'did not recognise' in error.detail


class TestAdvice:
    def test_every_refusal_says_what_to_do_instead(self):
        for code in (
            'FORBIDDEN',
            'NOT_FOUND',
            'CONFLICT',
            'STORE_UNAVAILABLE',
            'ELEMENT_CODE_UNRESOLVED',
            'SUPERSEDES_UNRESOLVED',
        ):
            error = parse_error_body(400, {'detail': 'x', 'errorCode': code})
            assert error.advice
            assert error.advice in error.message

    def test_being_refused_says_not_to_retry(self):
        error = parse_error_body(403, {'detail': 'x', 'errorCode': 'FORBIDDEN'})

        assert 'not retry' in error.advice.lower()

    def test_a_lost_race_says_to_read_again_first(self):
        # Only CONFLICT advice permits a second write.
        error = parse_error_body(409, {'detail': 'x', 'errorCode': 'CONFLICT'})

        assert 'read the artifact again' in error.advice.lower()

    def test_no_storage_folder_is_explained_as_the_persons_to_fix(self):
        error = parse_error_body(503, {'detail': 'x', 'errorCode': 'STORE_UNAVAILABLE'})

        assert 'person' in error.advice.lower()

    def test_a_code_this_client_has_not_heard_of_is_passed_through(self):
        error = parse_error_body(
            422, {'detail': 'something new', 'errorCode': 'NEW_RULE'}
        )

        assert error.error_code == 'NEW_RULE'
        assert 'something new' in error.message
        assert error.advice
