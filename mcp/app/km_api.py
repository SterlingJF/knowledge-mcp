# File: mcp/app/km_api.py
"""Backend HTTP client for every tool call. Requests are never retried and always carry agent headers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from app.errors import KmApiError, parse_error_body
from app.settings import AGENT_NAME

if TYPE_CHECKING:
    from app.settings import Settings

_client: httpx.Client | None = None
_settings: Settings | None = None


def configure(settings: Settings) -> None:
    """Called once by local entry point (app.entrypoints.local)."""
    global _client, _settings  # noqa: PLW0603 - module-level seam
    _settings = settings
    _client = httpx.Client(
        base_url=settings.API_ORIGIN,
        timeout=settings.API_TIMEOUT_SECONDS,
        headers={
            'User-Agent': f'{settings.APP_NAME}/1',
            # Backend request log (server/app/middleware/logging_middleware.py).
            'X-Km-Client': settings.APP_NAME,
            # Backend actor is `agent:<name>` (server/app/context.py).
            'X-Km-Agent': AGENT_NAME,
        },
    )


def origin() -> str:
    if _settings is None:
        msg = 'The API seam was used before it was configured.'
        raise RuntimeError(msg)
    return _settings.API_ORIGIN


def client() -> httpx.Client:
    if _client is None:
        msg = 'The API seam was used before it was configured.'
        raise RuntimeError(msg)
    return _client


def request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
    vault: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Send one request and return (body, receipt). Raise KmApiError on HTTP or transport failure."""
    cleaned = {key: value for key, value in (params or {}).items() if value is not None}
    request_headers = dict(headers or {})
    if vault:
        request_headers['X-Km-Vault'] = vault

    try:
        response = client().request(
            method,
            path,
            params=cleaned or None,
            json=json,
            headers=request_headers or None,
        )
    except httpx.RequestError as error:
        msg = (
            f'The backend at {origin()} could not be reached: {error}. '
            f'It may not be running yet. Do not retry in a loop; tell the person.'
        )
        raise KmApiError(msg, status=0) from error

    receipt = {
        'method': method,
        'url': str(response.request.url),
        'status': response.status_code,
        'elapsedMs': round(response.elapsed.total_seconds() * 1000, 1),
    }
    if vault:
        receipt['vault'] = vault
    if etag := response.headers.get('ETag'):
        receipt['etag'] = etag

    if response.status_code >= httpx.codes.BAD_REQUEST:
        raise parse_error_body(response.status_code, _decode(response))

    if response.status_code == httpx.codes.NO_CONTENT or not response.content:
        return None, receipt

    return _decode(response), receipt


def _decode(response: httpx.Response) -> Any:
    """Response JSON, or text on parse failure."""
    try:
        return response.json()
    except ValueError:
        return response.text


def probe() -> str:
    """Backend reachability status. Network errors become status text."""
    parsed = httpx.URL(origin())
    health = str(parsed.copy_with(raw_path=b'/health', query=None))
    try:
        response = client().get(health, timeout=2.0)
    except httpx.RequestError as error:
        return f'not answering at {origin()} ({type(error).__name__})'
    return f'answering at {origin()} ({response.status_code})'
