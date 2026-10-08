# File: mcp-server/tests/test_km_api.py
"""Vault selection uses a header. Requests without a vault omit the header."""

from __future__ import annotations

from datetime import timedelta

import httpx

from app import km_api


def _mock_client(seen: list[httpx.Request]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[], headers={"ETag": '"sha256-value"'})

    return httpx.Client(
        base_url="http://127.0.0.1:1/api/v1",
        transport=httpx.MockTransport(handler),
        # MockTransport never stamps elapsed. Receipt reads it.
        event_hooks={"response": [lambda r: setattr(r, "_elapsed", timedelta())]},
    )


def test_a_vault_rides_as_the_header(monkeypatch, configured):
    seen: list[httpx.Request] = []
    monkeypatch.setattr(km_api, "_client", _mock_client(seen))

    _, receipt = km_api.request("GET", "/artifacts", vault="abcd1234abcd1234")

    assert seen[0].headers["X-Km-Vault"] == "abcd1234abcd1234"
    assert receipt["vault"] == "abcd1234abcd1234"


def test_no_vault_sends_no_header(monkeypatch, configured):
    seen: list[httpx.Request] = []
    monkeypatch.setattr(km_api, "_client", _mock_client(seen))

    _, receipt = km_api.request("GET", "/artifacts")

    assert "X-Km-Vault" not in seen[0].headers
    assert "vault" not in receipt


def test_request_headers_and_response_etag_cross_the_seam(monkeypatch, configured):
    seen: list[httpx.Request] = []
    monkeypatch.setattr(km_api, "_client", _mock_client(seen))

    _, receipt = km_api.request(
        "PUT", "/artifacts/a", headers={"If-Match": '"sha256-old"'}
    )

    assert seen[0].headers["If-Match"] == '"sha256-old"'
    assert receipt["etag"] == '"sha256-value"'
