import asyncio
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status

from src.api.models import CheckoutRequest, Order, OrderStatus, Product
from src.chaos.state import chaos_engine

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1", tags=["E-Commerce API (ShopCore)"])

# In-memory mock database of products
SAMPLE_PRODUCTS: dict[str, Product] = {
    "prod-macbook": Product(
        id="prod-macbook",
        name="Apple MacBook Pro 16 M3 Max",
        category="Computers",
        price_cents=349900,
        stock_quantity=24,
    ),
    "prod-sony-wh": Product(
        id="prod-sony-wh",
        name="Sony WH-1000XM5 Noise Canceling Headphones",
        category="Audio",
        price_cents=39900,
        stock_quantity=85,
    ),
    "prod-keychron": Product(
        id="prod-keychron",
        name="Keychron Q1 Pro Wireless Custom Mechanical Keyboard",
        category="Peripherals",
        price_cents=19900,
        stock_quantity=110,
    ),
    "prod-dell-4k": Product(
        id="prod-dell-4k",
        name="Dell UltraSharp 32 4K USB-C Hub Monitor",
        category="Displays",
        price_cents=89900,
        stock_quantity=15,
    ),
}

ORDER_STORAGE: dict[str, Order] = {}


@router.get("/products", response_model=list[Product])
async def list_products():
    """List all available products in catalog."""
    return list(SAMPLE_PRODUCTS.values())


@router.get("/inventory/{product_id}")
async def check_inventory(product_id: str):
    """Check inventory for a specific SKU. Simulates downstream inventory microservice."""
    # Chaos Hook: Cascade Timeout
    if chaos_engine.inventory_timeout:
        logger.error(
            "inventory_cascade_timeout",
            service="inventory-service",
            product_id=product_id,
            delay_seconds=15,
        )
        # Simulate severe cascade delay
        await asyncio.sleep(15)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="504 Gateway Timeout: Downstream inventory microservice failed to respond within 15.0s",
        )

    if product_id not in SAMPLE_PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "product_id": product_id,
        "available_units": SAMPLE_PRODUCTS[product_id].stock_quantity,
        "status": "IN_STOCK",
    }


@router.post("/checkout", response_model=Order, status_code=status.HTTP_201_CREATED)
async def process_checkout(payload: CheckoutRequest):
    """
    Main e-commerce checkout endpoint.
    Performs inventory reservation, payment processing, and DB order persistence.
    Subject to active chaos fault injection for Datadog APM tracing and OpsMesh diagnosis.
    """
    logger.info(
        "checkout_attempt_started",
        customer_id=payload.customer_id,
        items_count=len(payload.items),
    )

    # 1. Chaos Hook: PostgreSQL Connection Pool Exhaustion
    if chaos_engine.postgres_pool_exhausted:
        logger.error(
            "db_connection_pool_exhausted",
            active_connections=chaos_engine.simulated_active_conns,
            max_connections=chaos_engine.simulated_max_conns,
            error_code="53300",
            source_file="src/api/routes.py:84",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections (active 15/10). Pool acquisition timed out after 3000ms.",
        )

    # 2. Chaos Hook: Database Schema Mismatch (Missing Column)
    if chaos_engine.schema_mismatch:
        logger.error(
            "sql_undefined_column_error",
            table="orders",
            column="tax_rate",
            source_file="src/api/routes.py:97",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="psycopg2.errors.UndefinedColumn: column orders.tax_rate does not exist at character 42. LINE 1: SELECT id, total, tax_rate FROM orders ...",
        )

    # 3. Chaos Hook: External Payment Gateway Flapping / Failure
    if chaos_engine.payment_gateway_flapping:
        logger.error(
            "payment_gateway_flapping_failure",
            provider="Stripe",
            endpoint="api.stripe.com/v1/charges",
            http_status=502,
            source_file="src/api/routes.py:111",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ExternalGatewayError: Failed to process credit card payment. Stripe API returned HTTP 502 Bad Gateway (Connection reset by peer).",
        )

    # 4. Chaos Hook: Memory Leak Allocation
    if chaos_engine.memory_leak:
        chaos_engine.inject_memory_leak(megabytes=10)
        logger.warning(
            "memory_leak_chunk_allocated",
            allocated_mb=10,
            total_leak_mb=len(chaos_engine.leaked_chunks) * 5,
        )

    # Validate items and calculate total
    total_cents = 0
    for item in payload.items:
        prod = SAMPLE_PRODUCTS.get(item.product_id)
        if not prod:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product SKU: {item.product_id}",
            )
        total_cents += prod.price_cents * item.quantity

    order_id = f"ord-{uuid.uuid4().hex[:8]}"
    order = Order(
        order_id=order_id,
        customer_id=payload.customer_id,
        status=OrderStatus.CONFIRMED,
        items=payload.items,
        total_amount_cents=total_cents,
    )
    ORDER_STORAGE[order_id] = order

    logger.info(
        "checkout_completed_successfully",
        order_id=order_id,
        total_cents=total_cents,
    )
    return order


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Retrieve an existing order by ID."""
    order = ORDER_STORAGE.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
