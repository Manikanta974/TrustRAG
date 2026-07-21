import asyncio

import httpx

from app.main import app


def test_health_check_returns_service_status() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "trustrag-api"}


def test_database_health_check_returns_ok_when_reachable() -> None:
    async def request_database_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/health/db")

    response = asyncio.run(request_database_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "trustrag-api", "database": "ok"}
