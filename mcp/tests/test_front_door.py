# File: mcp/tests/test_front_door.py
from __future__ import annotations

import json

import httpx
import pytest

from app.front_door import INVALID_REQUEST, FrontDoor
from app.settings import MCP_REVISION, META_PROTOCOL_VERSION_KEY

OLD_REVISION = '2025-11-25'


class Inner:
    def __init__(self) -> None:
        self.seen: bytes | None = None

    async def __call__(self, _scope, receive, send):
        chunks = []
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                break
            chunks.append(message.get('body', b''))
            if not message.get('more_body', False):
                break
        self.seen = b''.join(chunks)

        await send(
            {
                'type': 'http.response.start',
                'status': 200,
                'headers': [(b'content-type', b'application/json')],
            }
        )
        await send({'type': 'http.response.body', 'body': b'{"ok":true}'})


def _request(*, header_version: str | None, meta_version: str | None) -> dict:
    body: dict = {'jsonrpc': '2.0', 'id': 7, 'method': 'tools/list', 'params': {}}
    if meta_version is not None:
        body['params']['_meta'] = {META_PROTOCOL_VERSION_KEY: meta_version}
    headers = {'content-type': 'application/json'}
    if header_version is not None:
        headers['MCP-Protocol-Version'] = header_version
    return {'json': body, 'headers': headers}


async def _call(inner: Inner, method: str = 'POST', **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=FrontDoor(inner))
    async with httpx.AsyncClient(
        transport=transport, base_url='http://mcp.test'
    ) as client:
        return await client.request(method, '/mcp', **kwargs)


@pytest.mark.anyio
async def test_a_current_request_is_served_and_its_body_arrives_unchanged():
    inner = Inner()
    payload = _request(header_version=MCP_REVISION, meta_version=MCP_REVISION)

    response = await _call(inner, **payload)

    assert response.status_code == 200
    assert inner.seen is not None
    assert json.loads(inner.seen) == payload['json']


@pytest.mark.anyio
async def test_the_removed_get_stream_is_refused():
    inner = Inner()

    response = await _call(inner, method='GET')

    assert response.status_code == 405
    assert response.headers['allow'] == 'POST'
    assert response.json()['error']['code'] == INVALID_REQUEST
    assert inner.seen is None


@pytest.mark.anyio
async def test_the_legacy_handshake_is_refused():
    inner = Inner()

    response = await _call(
        inner,
        json={'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
        headers={'MCP-Protocol-Version': OLD_REVISION},
    )

    assert response.status_code == 400
    assert inner.seen is None


@pytest.mark.anyio
async def test_a_header_that_disagrees_with_meta_is_refused():
    inner = Inner()

    response = await _call(
        inner, **_request(header_version=OLD_REVISION, meta_version=MCP_REVISION)
    )

    assert response.status_code == 400
    assert inner.seen is None


@pytest.mark.anyio
async def test_meta_alone_is_not_enough():
    inner = Inner()

    response = await _call(
        inner, **_request(header_version=None, meta_version=MCP_REVISION)
    )

    assert response.status_code == 400
    assert inner.seen is None


@pytest.mark.anyio
async def test_a_header_alone_is_not_enough():
    inner = Inner()

    response = await _call(
        inner, **_request(header_version=MCP_REVISION, meta_version=None)
    )

    assert response.status_code == 400
    assert inner.seen is None


@pytest.mark.anyio
async def test_a_refusal_says_which_revision_is_served_and_how_to_send_it():
    inner = Inner()

    response = await _call(
        inner, **_request(header_version=OLD_REVISION, meta_version=OLD_REVISION)
    )

    message = response.json()['error']['message']
    assert MCP_REVISION in message
    assert 'MCP_SDK_GENERATION' in message
    assert response.headers['mcp-protocol-version'] == MCP_REVISION


@pytest.mark.anyio
async def test_what_follows_the_body_comes_from_the_real_connection():
    body = json.dumps(
        {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'tools/list',
            'params': {'_meta': {META_PROTOCOL_VERSION_KEY: MCP_REVISION}},
        }
    ).encode()
    after_the_body = {'type': 'test.marker'}

    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return after_the_body

    seen: list[dict] = []

    async def inner(_scope, inner_receive, send):
        await inner_receive()
        seen.append(await inner_receive())
        seen.append(await inner_receive())
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': b''})

    scope = {
        'type': 'http',
        'method': 'POST',
        'headers': [(b'mcp-protocol-version', MCP_REVISION.encode())],
    }

    async def send(_message):
        return None

    await FrontDoor(inner)(scope, receive, send)

    assert seen == [after_the_body, after_the_body]


@pytest.mark.anyio
async def test_an_unparseable_body_is_refused_rather_than_passed_on():
    inner = Inner()

    response = await _call(
        inner,
        content=b'not json',
        headers={'MCP-Protocol-Version': MCP_REVISION},
    )

    assert response.status_code == 400
    assert inner.seen is None
