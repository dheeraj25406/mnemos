from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from mnemos.api.app import app
from mnemos.client import AsyncMnemos


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-Mnemos-API-Key": "mnk_test_secret_key_12345"},
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_api_health_endpoint(api_client: httpx.AsyncClient):
    resp = await api_client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["product"] == "Mnemos"
    assert data["database"]["connected"] is True


@pytest.mark.asyncio
async def test_api_memory_lifecycle(api_client: httpx.AsyncClient):
    # Ingest
    payload = {
        "content": "Elena Rostova joined HyperScale as Lead Architect on 2024-04-01",
        "memory_type": "observation",
        "valid_from": "2024-04-01T00:00:00Z",
        "importance": 0.85,
    }
    create_resp = await api_client.post("/v1/memories", json=payload)
    assert create_resp.status_code == 201
    mem_data = create_resp.json()
    assert "memory_id" in mem_data
    mid = mem_data["memory_id"]

    # Get memory detail
    detail_resp = await api_client.get(f"/v1/memories/{mid}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == mid
    assert "HyperScale" in detail["normalized_content"]

    # Hybrid Search
    search_payload = {
        "query": "Who is Lead Architect at HyperScale?",
        "top_k": 3,
        "valid_at": "2024-05-01T00:00:00Z",
    }
    search_resp = await api_client.post("/v1/memories/search", json=search_payload)
    assert search_resp.status_code == 200
    s_data = search_resp.json()
    assert s_data["total_found"] >= 1
    assert any("HyperScale" in m["content"] for m in s_data["memories"])

    # Metrics endpoint
    metrics_resp = await api_client.get("/v1/metrics")
    assert metrics_resp.status_code == 200
    m_data = metrics_resp.json()
    assert m_data["memories_total"] >= 1

    # Delete memory
    del_resp = await api_client.delete(f"/v1/memories/{mid}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_sdk_async_client_flow(db_session: AsyncSession):
    # Test SDK using ASGI transport client
    sdk = AsyncMnemos(base_url="http://testserver", api_key="mnk_test_secret_key_12345")
    # Swap internal transport to test ASGI app
    sdk._client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"X-Mnemos-API-Key": "mnk_test_secret_key_12345"},
    )

    # Ingest via SDK
    res = await sdk.add(
        content="Marcus Vance works at Orbital Robotics in Zurich as of 2024-03-15",
        user_id="agent-007",
        valid_from=datetime(2024, 3, 15, tzinfo=timezone.utc),
    )
    assert res["is_duplicate"] is False
    assert "memory_id" in res

    # Search via SDK
    search_res = await sdk.search(
        query="Where does Marcus Vance work?",
        valid_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    assert search_res.total_found >= 1

    # Clean up
    await sdk.delete(res["memory_id"])
    await sdk.close()
