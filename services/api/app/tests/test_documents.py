import asyncio

import httpx
from sqlalchemy import text

from app.db.session import engine
from app.main import app

NORTHSTAR_SLUG = "northstar-labs"

INTERN_PROFILE_ID = "20000000-0000-0000-0000-000000000005"
NORTHSTAR_ORG_ID = "10000000-0000-0000-0000-000000000001"

EMPLOYEE_HANDBOOK_ID = "80000000-0000-0000-0000-000000000001"
LEAVE_POLICY_ID = "80000000-0000-0000-0000-000000000002"
ENGINEERING_ARCHITECTURE_ID = "80000000-0000-0000-0000-000000000003"
SALARY_BANDS_ID = "80000000-0000-0000-0000-000000000004"
LEGAL_CONTRACT_ID = "80000000-0000-0000-0000-000000000005"
QUARANTINED_DOC_ID = "80000000-0000-0000-0000-000000000006"


def _request(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    json: dict | None = None,
) -> httpx.Response:
    async def call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, headers=headers or {}, json=json)

    return asyncio.run(call())


def _headers(email: str) -> dict[str, str]:
    return {"X-Dev-User-Email": email, "X-Dev-Organization-Slug": NORTHSTAR_SLUG}


def test_admin_sees_owned_and_role_granted_documents() -> None:
    response = _request("GET", "/v1/documents", headers=_headers("admin@northstarlabs.demo"))

    assert response.status_code == 200
    document_ids = {doc["id"] for doc in response.json()}
    assert document_ids == {
        EMPLOYEE_HANDBOOK_ID,
        LEAVE_POLICY_ID,
        SALARY_BANDS_ID,
        LEGAL_CONTRACT_ID,
    }


def test_engineer_sees_engineering_accessible_documents() -> None:
    response = _request("GET", "/v1/documents", headers=_headers("engineer@northstarlabs.demo"))

    assert response.status_code == 200
    document_ids = {doc["id"] for doc in response.json()}
    assert document_ids == {EMPLOYEE_HANDBOOK_ID, LEAVE_POLICY_ID, ENGINEERING_ARCHITECTURE_ID}


def test_intern_cannot_see_restricted_documents() -> None:
    response = _request("GET", "/v1/documents", headers=_headers("intern@northstarlabs.demo"))

    assert response.status_code == 200
    document_ids = {doc["id"] for doc in response.json()}
    assert SALARY_BANDS_ID not in document_ids
    assert LEGAL_CONTRACT_ID not in document_ids
    assert ENGINEERING_ARCHITECTURE_ID in document_ids


def test_no_one_sees_quarantined_document() -> None:
    for email in ("admin@northstarlabs.demo", "engineer@northstarlabs.demo"):
        response = _request("GET", "/v1/documents", headers=_headers(email))
        document_ids = {doc["id"] for doc in response.json()}
        assert QUARANTINED_DOC_ID not in document_ids


def test_documents_list_requires_dev_headers() -> None:
    response = _request("GET", "/v1/documents")

    assert response.status_code == 401


def test_documents_list_rejects_unknown_user() -> None:
    response = _request("GET", "/v1/documents", headers=_headers("nobody@northstarlabs.demo"))

    assert response.status_code == 401


def test_document_access_true_with_reason_for_owned_document() -> None:
    response = _request(
        "GET",
        f"/v1/documents/{EMPLOYEE_HANDBOOK_ID}/access",
        headers=_headers("admin@northstarlabs.demo"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["reason"] == "owner"


def test_document_access_false_for_intern_on_restricted_document() -> None:
    response = _request(
        "GET",
        f"/v1/documents/{SALARY_BANDS_ID}/access",
        headers=_headers("intern@northstarlabs.demo"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["reason"] == "no_grant"


def test_document_access_false_for_quarantined_document() -> None:
    response = _request(
        "GET",
        f"/v1/documents/{QUARANTINED_DOC_ID}/access",
        headers=_headers("admin@northstarlabs.demo"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["reason"] == "no_ready_version"


def test_document_access_requires_dev_headers() -> None:
    response = _request("GET", f"/v1/documents/{EMPLOYEE_HANDBOOK_ID}/access")

    assert response.status_code == 401


def _valid_create_payload(**overrides: object) -> dict:
    payload = {
        "title": "Q3 Onboarding Guide",
        "description": "Draft onboarding guide for new hires.",
        "classification": "internal",
        "original_filename": "q3-onboarding-guide.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1024,
    }
    payload.update(overrides)
    return payload


def test_admin_can_create_document_metadata() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("admin@northstarlabs.demo"),
        json=_valid_create_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Q3 Onboarding Guide"
    assert body["status"] == "active"
    assert body["version_number"] == 1
    assert body["version_status"] == "pending"


def test_employee_can_create_document_metadata() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("employee@northstarlabs.demo"),
        json=_valid_create_payload(title="HR Intake Notes"),
    )

    assert response.status_code == 201
    assert response.json()["title"] == "HR Intake Notes"


def test_create_document_requires_dev_headers() -> None:
    response = _request("POST", "/v1/documents", json=_valid_create_payload())

    assert response.status_code == 401


def test_create_document_rejects_invalid_mime_type() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("admin@northstarlabs.demo"),
        json=_valid_create_payload(mime_type="application/zip"),
    )

    assert response.status_code == 422


def test_create_document_rejects_oversized_file() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("admin@northstarlabs.demo"),
        json=_valid_create_payload(file_size_bytes=21 * 1024 * 1024),
    )

    assert response.status_code == 422


def test_create_document_rejects_invalid_classification() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("admin@northstarlabs.demo"),
        json=_valid_create_payload(classification="top-secret"),
    )

    assert response.status_code == 422


def test_create_document_rejects_department_from_other_organization() -> None:
    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("admin@northstarlabs.demo"),
        json=_valid_create_payload(department_id="99999999-0000-0000-0000-000000000001"),
    )

    assert response.status_code == 422


def test_create_document_ignores_client_supplied_identity_fields() -> None:
    spoofed_payload = _valid_create_payload(
        title="Spoof Attempt",
        organization_id="99999999-0000-0000-0000-000000000001",
        owner_profile_id="20000000-0000-0000-0000-000000000001",
    )

    response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("intern@northstarlabs.demo"),
        json=spoofed_payload,
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    with engine.connect() as connection:
        row = connection.execute(
            text("select owner_profile_id, organization_id from documents where id = :id"),
            {"id": document_id},
        ).mappings().first()
    assert str(row["owner_profile_id"]) == INTERN_PROFILE_ID
    assert str(row["organization_id"]) == NORTHSTAR_ORG_ID


def test_newly_created_document_not_yet_visible_in_list_or_access() -> None:
    create_response = _request(
        "POST",
        "/v1/documents",
        headers=_headers("engineer@northstarlabs.demo"),
        json=_valid_create_payload(title="Draft Runbook"),
    )
    document_id = create_response.json()["id"]

    list_response = _request(
        "GET", "/v1/documents", headers=_headers("engineer@northstarlabs.demo")
    )
    assert document_id not in {doc["id"] for doc in list_response.json()}

    access_response = _request(
        "GET",
        f"/v1/documents/{document_id}/access",
        headers=_headers("engineer@northstarlabs.demo"),
    )
    body = access_response.json()
    assert body["allowed"] is False
    assert body["reason"] == "no_ready_version"
