import asyncio

import httpx

from app.main import app

NORTHSTAR_SLUG = "northstar-labs"

EMPLOYEE_HANDBOOK_ID = "80000000-0000-0000-0000-000000000001"
LEAVE_POLICY_ID = "80000000-0000-0000-0000-000000000002"
ENGINEERING_ARCHITECTURE_ID = "80000000-0000-0000-0000-000000000003"
SALARY_BANDS_ID = "80000000-0000-0000-0000-000000000004"
LEGAL_CONTRACT_ID = "80000000-0000-0000-0000-000000000005"
QUARANTINED_DOC_ID = "80000000-0000-0000-0000-000000000006"


def _request(
    method: str, path: str, headers: dict[str, str] | None = None
) -> httpx.Response:
    async def call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, headers=headers or {})

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
