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
async def test_chaos_status_snapshot():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/chaos/status")
        assert res.status_code == 200
        data = res.json()
        assert data["is_healthy"] is True
        assert data["simulated_active_conns"] == 2


@pytest.mark.asyncio
async def test_inject_postgres_pool_triggers_503():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Inject fault
        inject_res = await client.post("/chaos/inject/postgres-pool")
        assert inject_res.status_code == 200
        assert inject_res.json()["postgres_pool_exhausted"] is True

        # Verify checkout fails with 503
        checkout_res = await client.post(
            "/api/v1/checkout",
            json={
                "customer_id": "cust-victim",
                "items": [{"product_id": "prod-macbook", "quantity": 1}],
                "shipping_address": "Rua do Caos 100",
            },
        )
        assert checkout_res.status_code == 503
        assert "psycopg2.OperationalError" in checkout_res.json()["detail"]

        # Health endpoint should report DEGRADED
        health_res = await client.get("/health")
        assert health_res.status_code == 503
        assert health_res.json()["status"] == "DEGRADED"


@pytest.mark.asyncio
async def test_inject_payment_flap_triggers_502():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/chaos/inject/payment-flap")

        checkout_res = await client.post(
            "/api/v1/checkout",
            json={
                "customer_id": "cust-victim",
                "items": [{"product_id": "prod-macbook", "quantity": 1}],
                "shipping_address": "Rua do Caos 100",
            },
        )
        assert checkout_res.status_code == 502
        assert "ExternalGatewayError" in checkout_res.json()["detail"]


@pytest.mark.asyncio
async def test_inject_schema_mismatch_triggers_500():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/chaos/inject/schema-mismatch")

        checkout_res = await client.post(
            "/api/v1/checkout",
            json={
                "customer_id": "cust-victim",
                "items": [{"product_id": "prod-macbook", "quantity": 1}],
                "shipping_address": "Rua do Caos 100",
            },
        )
        assert checkout_res.status_code == 500
        assert "UndefinedColumn" in checkout_res.json()["detail"]


@pytest.mark.asyncio
async def test_inject_memory_leak():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/chaos/inject/memory-leak?megabytes=25")
        assert res.status_code == 200
        data = res.json()
        assert data["memory_leak"] is True
        assert data["memory_leak_mb"] >= 25


@pytest.mark.asyncio
async def test_chaos_roulette():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/chaos/roulette")
        assert res.status_code == 200
        data = res.json()
        assert "roulette_outcome" in data
        assert data["current_state"]["is_healthy"] is False


@pytest.mark.asyncio
async def test_chaos_reset():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Break system
        await client.post("/chaos/inject/postgres-pool")
        await client.post("/chaos/inject/payment-flap")

        # Reset
        reset_res = await client.post("/chaos/reset")
        assert reset_res.status_code == 200
        data = reset_res.json()
        assert data["is_healthy"] is True
        assert data["postgres_pool_exhausted"] is False
        assert data["payment_gateway_flapping"] is False
