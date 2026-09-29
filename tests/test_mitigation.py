import pytest
from httpx import ASGITransport, AsyncClient

from src.chaos.state import chaos_engine
from src.main import app


@pytest.fixture(autouse=True)
def reset_chaos_state():
    chaos_engine.reset_all()
    yield
    chaos_engine.reset_all()


@pytest.mark.asyncio
async def test_mitigate_postgres_pool_restores_service():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Break DB Pool
        await client.post("/chaos/inject/postgres-pool")

        # 2. Call OpsMesh Tier 1 Runtime Mitigation
        mitigate_res = await client.post(
            "/operations/mitigate",
            json={
                "action_type": "DATABASE_CONNECTION_SCALE",
                "requester": "OpsMesh-IncidentSupervisorAgent",
                "details": "Pool scaled up, idle backends terminated.",
            },
        )
        assert mitigate_res.status_code == 200
        data = mitigate_res.json()
        assert data["status"] == "SUCCESS"
        assert "Reset DB connection pool" in data["actions_applied"][0]

        # 3. Verify checkout succeeds now
        checkout_res = await client.post(
            "/api/v1/checkout",
            json={
                "customer_id": "cust-restored",
                "items": [{"product_id": "prod-macbook", "quantity": 1}],
                "shipping_address": "Rua da Paz 200",
            },
        )
        assert checkout_res.status_code == 201


@pytest.mark.asyncio
async def test_mitigate_circuit_breaker_and_schema():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Break with schema and payment flap
        await client.post("/chaos/inject/schema-mismatch")
        await client.post("/chaos/inject/payment-flap")

        # Mitigate both
        mitigate_res = await client.post(
            "/operations/mitigate",
            json={
                "action_type": "ALL",
                "requester": "OpsMesh-Automated-Commander",
                "details": "Emergency full recovery.",
            },
        )
        assert mitigate_res.status_code == 200
        assert mitigate_res.json()["current_state"]["is_healthy"] is True
