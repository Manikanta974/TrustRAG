import asyncio

import httpx

from app.main import app

NORTHSTAR_SLUG = "northstar-labs"


def _get(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async def call() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get(path, headers=headers or {})

    return asyncio.run(call())


def test_me_returns_membership_for_valid_seeded_user() -> None:
    response = _get(
        "/v1/me",
        headers={
            "X-Dev-User-Email": "engineer@northstarlabs.demo",
            "X-Dev-Organization-Slug": NORTHSTAR_SLUG,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "engineer@northstarlabs.demo"
    assert body["organization_slug"] == NORTHSTAR_SLUG
    assert body["role_name"] == "employee"
    assert body["department_name"] == "Engineering"


def test_me_requires_dev_headers() -> None:
    response = _get("/v1/me")

    assert response.status_code == 401


def test_me_rejects_unknown_user() -> None:
    response = _get(
        "/v1/me",
        headers={
            "X-Dev-User-Email": "nobody@northstarlabs.demo",
            "X-Dev-Organization-Slug": NORTHSTAR_SLUG,
        },
    )

    assert response.status_code == 401


def test_me_rejects_wrong_organization_slug() -> None:
    response = _get(
        "/v1/me",
        headers={
            "X-Dev-User-Email": "engineer@northstarlabs.demo",
            "X-Dev-Organization-Slug": "wrong-org",
        },
    )

    assert response.status_code == 401
