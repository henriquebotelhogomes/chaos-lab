import pytest
from httpx import ASGITransport, AsyncClient

from src.chaos.state import chaos_engine
from src.main import app


@pytest.fixture(autouse=True)
def reset_chaos_state():
    """Ensure chaos engine is completely reset before each test."""
    chaos_engine.reset_all()
    yield
    chaos_engine.reset_all()


@pytest.mark.asyncio
async def test_health_check_healthy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["chaos_status"]["is_healthy"] is True


@pytest.mark.asyncio
async def test_scalar_documentation_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/docs")
        assert res.status_code == 200
        assert "scalar" in res.text.lower() or "html" in res.text.lower()


@pytest.mark.asyncio
async def test_dashboard_ui_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert "Chaos Lab" in res.text
        assert "Roleta Russa do Caos" in res.text


@pytest.mark.asyncio
async def test_list_products():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/products")
        assert res.status_code == 200
        products = res.json()
        assert len(products) >= 4
        assert any(p["id"] == "prod-macbook" for p in products)


@pytest.mark.asyncio
async def test_inventory_check_normal():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/inventory/prod-macbook")
        assert res.status_code == 200
        data = res.json()
        assert data["product_id"] == "prod-macbook"
        assert data["status"] == "IN_STOCK"


@pytest.mark.asyncio
async def test_checkout_success_normal_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "customer_id": "cust-test-123",
            "items": [{"product_id": "prod-macbook", "quantity": 1}],
            "shipping_address": "Test Avenue 100",
        }
        res = await client.post("/api/v1/checkout", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "CONFIRMED"
        assert data["customer_id"] == "cust-test-123"
        assert data["total_amount_cents"] == 349900
        assert data["order_id"].startswith("ord-")
