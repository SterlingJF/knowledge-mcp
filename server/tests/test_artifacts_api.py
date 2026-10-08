# File: server/tests/test_artifacts_api.py

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.conftest import (
    AGENT,
    AGENT_HEADERS,
    DECISION,
    DECISION_RECORD,
    PERSON,
    UNCLOSABLE,
    UNIVERSE,
    create,
    creation_payload,
)

if TYPE_CHECKING:
    from pathlib import Path

    from fastapi.testclient import TestClient


def _etag(client: TestClient, artifact_id: str) -> str:
    return client.get(f"/api/v1/artifacts/{artifact_id}").headers["ETag"]


def _update(
    client: TestClient,
    artifact_id: str,
    payload: dict,
    headers: dict[str, str] | None = None,
):
    request_headers = dict(headers or {})
    request_headers["If-Match"] = _etag(client, artifact_id)
    return client.put(
        f"/api/v1/artifacts/{artifact_id}", json=payload, headers=request_headers
    )


def test_create_stamps_the_server_owned_fields(client: TestClient):
    artifact = create(client)

    assert artifact["createdBy"] == PERSON
    assert artifact["status"] == "DRAFT"
    assert artifact["version"] == 1
    record = artifact["data"][DECISION][0]
    assert record["id"]
    assert record["observed_at"]


def test_create_stamps_an_agent_when_it_identifies_itself(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "Files, not a database.",
                    "asserted_by": AGENT,
                    "status": "conjecture",
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload, headers=AGENT_HEADERS)

    assert response.status_code == 201
    assert response.json()["createdBy"] == AGENT


def test_created_by_is_never_accepted_from_the_payload(client: TestClient):
    payload = creation_payload()
    payload["createdBy"] = "local-principal:someone-else"
    assert client.post("/api/v1/artifacts", json=payload).status_code == 422


def test_status_is_never_accepted_on_create_or_update(client: TestClient):
    payload = creation_payload()
    payload["status"] = "COMMITTED"
    assert client.post("/api/v1/artifacts", json=payload).status_code == 422

    artifact = create(client)
    response = _update(client, artifact["id"], {"status": "COMMITTED"})
    assert response.status_code == 422


def test_get_and_list_and_delete(client: TestClient):
    artifact = create(client)
    artifact_id = artifact["id"]

    fetched = client.get(f"/api/v1/artifacts/{artifact_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == artifact_id
    assert fetched.headers["ETag"].startswith('"sha256-')

    listed = client.get("/api/v1/artifacts")
    assert [item["id"] for item in listed.json()] == [artifact_id]
    assert "data" not in listed.json()[0]
    assert "report" not in listed.json()[0]

    assert client.delete(f"/api/v1/artifacts/{artifact_id}").status_code == 204
    assert client.get(f"/api/v1/artifacts/{artifact_id}").status_code == 404
    assert client.get("/api/v1/artifacts").json() == []


def test_list_filters(client: TestClient):
    create(client)

    assert len(client.get("/api/v1/artifacts?status=DRAFT").json()) == 1
    assert len(client.get("/api/v1/artifacts?status=COMMITTED").json()) == 0
    assert (
        len(client.get(f"/api/v1/artifacts?artifactType={DECISION_RECORD}").json()) == 1
    )
    assert len(client.get("/api/v1/artifacts?artifactType=a0000").json()) == 0
    # Decision record spans design and discovery (UniverseIndex.ordering_values_for_type).
    assert len(client.get("/api/v1/artifacts?orderingFrameValue=design").json()) == 1
    assert len(client.get("/api/v1/artifacts?orderingFrameValue=discovery").json()) == 1
    assert len(client.get("/api/v1/artifacts?orderingFrameValue=operate").json()) == 0


def test_update_is_per_element_code_replacement(client: TestClient):
    artifact = create(client)
    artifact_id = artifact["id"]

    response = _update(
        client,
        artifact_id,
        {
            "dataToUpdate": {
                "ebxtg": [
                    {
                        "element": "ebxtg",
                        "value": "Artifacts stop fitting in one folder.",
                        "asserted_by": PERSON,
                        "status": "modelled",
                    }
                ]
            }
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["data"][DECISION][0]["value"] == "Files, not a database."
    assert (
        updated["data"]["ebxtg"][0]["value"] == "Artifacts stop fitting in one folder."
    )
    assert updated["version"] == 2


def test_update_with_an_empty_list_clears_and_reports_dropped_history(
    client: TestClient,
):
    artifact = create(client)
    response = _update(client, artifact["id"], {"dataToUpdate": {DECISION: []}})

    assert response.status_code == 200
    body = response.json()
    assert DECISION not in body["data"]
    assert any(
        finding["kind"] == "history-dropped" for finding in body["report"]["findings"]
    )


def test_a_correction_keeps_the_superseded_record(client: TestClient):
    artifact = create(client)
    original = artifact["data"][DECISION][0]

    response = _update(
        client,
        artifact["id"],
        {
            "dataToUpdate": {
                DECISION: [
                    {
                        "element": DECISION,
                        "value": "Files, in a folder the person picks.",
                        "asserted_by": PERSON,
                        "status": "contracted",
                        "supersedes": original["id"],
                    },
                    {
                        "id": original["id"],
                        "element": DECISION,
                        "value": original["value"],
                        "asserted_by": PERSON,
                        "status": "contracted",
                    },
                ]
            }
        },
    )

    assert response.status_code == 200, response.text
    records = response.json()["data"][DECISION]
    assert len(records) == 2
    assert {record["id"] for record in records} >= {original["id"]}
    assert records[0]["supersedes"] == original["id"]


def test_a_client_cannot_choose_an_instance_id(client: TestClient):
    invented = "55555555-5555-4555-8555-555555555555"
    artifact = create(client)

    response = _update(
        client,
        artifact["id"],
        {
            "dataToUpdate": {
                "ebxtg": [
                    {
                        "id": invented,
                        "element": "ebxtg",
                        "value": "A reversal condition.",
                        "asserted_by": PERSON,
                        "status": "modelled",
                    }
                ]
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["ebxtg"][0]["id"] != invented


def test_an_agent_may_not_commit(client: TestClient):
    artifact = create(client)
    response = client.post(
        f"/api/v1/artifacts/{artifact['id']}/status",
        json={"status": "COMMITTED"},
        headers=AGENT_HEADERS,
    )

    assert response.status_code == 403
    assert response.json()["errorCode"] == "FORBIDDEN"


def test_a_person_may_commit(client: TestClient):
    artifact = create(client)
    response = client.post(
        f"/api/v1/artifacts/{artifact['id']}/status", json={"status": "COMMITTED"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMMITTED"


def test_an_agent_may_not_assert_as_somebody_else(client: TestClient):
    artifact = create(client)
    response = _update(
        client,
        artifact["id"],
        {
            "dataToUpdate": {
                DECISION: [
                    {
                        "element": DECISION,
                        "value": "Asserted as the person, by an agent.",
                        "asserted_by": PERSON,
                        "status": "contracted",
                    }
                ]
            }
        },
        AGENT_HEADERS,
    )

    assert response.status_code == 403


def test_update_requires_if_match(client: TestClient):
    artifact = create(client)

    response = client.put(
        f"/api/v1/artifacts/{artifact['id']}",
        json={"name": "A renamed decision record"},
    )

    assert response.status_code == 428
    assert response.json()["errorCode"] == "PRECONDITION_REQUIRED"


def test_update_returns_a_new_etag(client: TestClient):
    artifact = create(client)
    before = _etag(client, artifact["id"])

    response = client.put(
        f"/api/v1/artifacts/{artifact['id']}",
        json={"name": "A renamed decision record"},
        headers={"If-Match": before},
    )

    assert response.status_code == 200
    assert response.headers["ETag"] != before


def test_update_refuses_a_stale_caller_etag(client: TestClient, store_root: Path):
    artifact = create(client)
    before = _etag(client, artifact["id"])
    path = next((store_root / "Efforts").glob("artifact-*.md"))
    path.write_text(f"{path.read_text(encoding='utf-8')}\nedited by a person\n")

    response = client.put(
        f"/api/v1/artifacts/{artifact['id']}",
        json={"name": "A stale decision record"},
        headers={"If-Match": before},
    )

    assert response.status_code == 409
    assert response.json()["fields"]["expectedEtag"] == before


def test_a_malformed_agent_claim_is_treated_as_the_person(client: TestClient):
    """A typo must not lock a person out of their own files."""
    response = client.post(
        "/api/v1/artifacts",
        json=creation_payload(),
        headers={"X-Km-Agent": "Not A Slug!"},
    )

    assert response.status_code == 201
    assert response.json()["createdBy"] == PERSON


def test_refuses_an_unresolvable_element_code(client: TestClient):
    payload = creation_payload(
        data={
            "ezzzz": [
                {
                    "element": "ezzzz",
                    "value": "x",
                    "asserted_by": PERSON,
                    "status": "contracted",
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "ELEMENT_CODE_UNRESOLVED"


def test_refuses_a_status_the_universe_does_not_declare(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "x",
                    "asserted_by": PERSON,
                    "status": "vibes",
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "INSTANCE_STATUS_UNDECLARED"


def test_refuses_exhaustive_true_on_an_unclosable_element(client: TestClient):
    payload = creation_payload(
        data={
            UNCLOSABLE: [
                {
                    "element": UNCLOSABLE,
                    "value": "Everything, apparently.",
                    "asserted_by": PERSON,
                    "status": "modelled",
                    "exhaustive": True,
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "EXHAUSTIVE_ON_UNCLOSABLE_ELEMENT"


def test_allows_exhaustive_true_where_closable_is_absent(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "Files.",
                    "asserted_by": PERSON,
                    "status": "contracted",
                    "exhaustive": True,
                }
            ]
        }
    )
    assert client.post("/api/v1/artifacts", json=payload).status_code == 201


def test_refuses_two_un_superseded_records_with_the_same_triple(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "One",
                    "asserted_by": PERSON,
                    "status": "contracted",
                },
                {
                    "element": DECISION,
                    "value": "Two",
                    "asserted_by": PERSON,
                    "status": "contracted",
                },
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "DUPLICATE_UNSUPERSEDED_INSTANCE"


def test_allows_two_live_records_that_differ_by_asserting_party(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "One",
                    "asserted_by": PERSON,
                    "status": "contracted",
                },
                {
                    "element": DECISION,
                    "value": "Two",
                    "asserted_by": AGENT,
                    "status": "contracted",
                },
            ]
        }
    )
    assert client.post("/api/v1/artifacts", json=payload).status_code == 201


def test_refuses_a_supersedes_that_resolves_to_nothing(client: TestClient):
    payload = creation_payload(
        data={
            DECISION: [
                {
                    "element": DECISION,
                    "value": "Replacing a ghost.",
                    "asserted_by": PERSON,
                    "status": "contracted",
                    "supersedes": "99999999-9999-4999-8999-999999999999",
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "SUPERSEDES_UNRESOLVED"


def test_refuses_an_unknown_universe_id(client: TestClient):
    payload = creation_payload(universe={"id": "not-a-universe", "version": "1.0"})
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 422
    assert response.json()["errorCode"] == "UNIVERSE_UNKNOWN"


def test_serves_an_artifact_pinning_a_version_this_image_lacks_and_reports_it(
    client: TestClient,
):
    """Refusing would make a person's own file unreadable after an upgrade."""
    payload = creation_payload(universe={"id": UNIVERSE["id"], "version": "0.4"})
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 201
    assert any(
        finding["kind"] == "universe-version"
        for finding in response.json()["report"]["findings"]
    )


def test_an_incomplete_artifact_is_accepted_and_reported(client: TestClient):
    artifact = create(client)
    kinds = {finding["kind"] for finding in artifact["report"]["findings"]}

    assert "composition-core-missing" in kinds
    assert all(
        finding["severity"] in {"info", "warning"}
        for finding in artifact["report"]["findings"]
    )


def test_a_dangling_link_is_reported_not_refused(client: TestClient):
    payload = creation_payload(
        links={
            "eyhkm": [
                {
                    "artifactId": "99999999-9999-4999-8999-999999999999",
                    "instanceId": "88888888-8888-4888-8888-888888888888",
                }
            ]
        }
    )
    response = client.post("/api/v1/artifacts", json=payload)

    assert response.status_code == 201
    assert any(
        finding["kind"] == "dangling-link"
        for finding in response.json()["report"]["findings"]
    )


def test_a_shared_instance_id_is_reported_not_refused(
    client: TestClient, store_root: Path
):
    original = create(client)
    source = next(store_root.rglob("*.md"))
    copy = source.parent / "Copy of the same artifact.md"
    copy.write_bytes(
        source.read_bytes().replace(
            original["id"].encode(), b"7c9e1b40-5c2a-4f61-9a3d-2b6f8e0d1234"
        )
    )

    body = client.get(f"/api/v1/artifacts/{original['id']}").json()

    assert any(
        finding["kind"] == "ownership-shared" for finding in body["report"]["findings"]
    )


def test_a_hand_edited_file_is_coerced_and_the_coercion_is_reported(
    client: TestClient, store_root: Path
):
    artifact = create(client)
    path = next(store_root.rglob("*.md"))
    path.write_bytes(
        path.read_bytes().replace(
            b"lastReviewedDate: null", b"lastReviewedDate: 2025-05-18"
        )
    )

    body = client.get(f"/api/v1/artifacts/{artifact['id']}").json()

    assert body["lastReviewedDate"] == "2025-05-18T00:00:00Z"
    assert any(finding["kind"] == "coerced" for finding in body["report"]["findings"])
