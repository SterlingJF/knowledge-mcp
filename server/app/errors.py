# File: server/app/errors.py
"""`KmError` responses use `{detail, errorCode, fields}` (`app.factory._km_error_handler`). Incomplete artifacts use reports (`app.store.validation.build_report`)."""

from __future__ import annotations

from http import HTTPStatus


class KmError(Exception):
    status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = 'INTERNAL_ERROR'

    def __init__(
        self, detail: str, fields: dict[str, str | None] | None = None
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.fields = fields


class NotFoundError(KmError):
    """The named artifact, universe or guidance document does not exist."""

    status = HTTPStatus.NOT_FOUND
    code = 'NOT_FOUND'


class RefusedError(KmError):
    status = HTTPStatus.UNPROCESSABLE_ENTITY
    code = 'UNPROCESSABLE_ENTITY'


class UnresolvedElementError(RefusedError):
    code = 'ELEMENT_CODE_UNRESOLVED'


class UndeclaredStatusError(RefusedError):
    code = 'INSTANCE_STATUS_UNDECLARED'


class ExhaustiveOnUnclosableError(RefusedError):
    code = 'EXHAUSTIVE_ON_UNCLOSABLE_ELEMENT'


class DuplicateLiveInstanceError(RefusedError):
    code = 'DUPLICATE_UNSUPERSEDED_INSTANCE'


class UnresolvedSupersedesError(RefusedError):
    code = 'SUPERSEDES_UNRESOLVED'


class UnknownUniverseError(RefusedError):
    """Uncarried universe versions are served and reported (`app.store.validation.resolve_universe`)."""

    code = 'UNIVERSE_UNKNOWN'


class UnusablePathError(RefusedError):
    pass


class ForbiddenError(KmError):
    """Only a person may commit or assert in another's name (app.store.service)."""

    status = HTTPStatus.FORBIDDEN
    code = 'FORBIDDEN'


class ConflictError(KmError):
    status = HTTPStatus.CONFLICT
    code = 'CONFLICT'


class PreconditionRequiredError(KmError):
    status = HTTPStatus.PRECONDITION_REQUIRED
    code = 'PRECONDITION_REQUIRED'


class StoreUnavailableError(KmError):
    """Unavailable storage is a readiness state (`app.factory.create_app`)."""

    status = HTTPStatus.SERVICE_UNAVAILABLE
    code = 'STORE_UNAVAILABLE'
