import random
from typing import Any

import structlog
from fastapi import APIRouter

from src.chaos.state import chaos_engine

logger = structlog.get_logger()
router = APIRouter(prefix="/chaos", tags=["Chaos Engineering & Fault Injection"])


@router.get("/status")
async def get_chaos_status() -> dict[str, Any]:
    """Returns current active chaos states, memory leaks, and incident event logs."""
    return chaos_engine.get_snapshot()


@router.post("/inject/postgres-pool")
async def inject_postgres_pool():
    """Simulate Postgres Connection Pool Exhaustion (active connections 15/10)."""
    logger.warn("chaos_inject_postgres_pool_triggered")
    return chaos_engine.inject_postgres_pool()


@router.post("/inject/timeout")
async def inject_timeout():
    """Simulate Cascade Timeout in downstream inventory (15s latency -> 504 Gateway Timeout)."""
    logger.warn("chaos_inject_timeout_triggered")
    return chaos_engine.inject_timeout()


@router.post("/inject/memory-leak")
async def inject_memory_leak(megabytes: int = 25):
    """Simulate Unbounded Memory Leak by allocating uncollected byte buffers."""
    logger.warn("chaos_inject_memory_leak_triggered", megabytes=megabytes)
    return chaos_engine.inject_memory_leak(megabytes=megabytes)


@router.post("/inject/payment-flap")
async def inject_payment_flap():
    """Simulate Payment Gateway Flapping (Stripe/Adyen returning HTTP 502/500)."""
    logger.warn("chaos_inject_payment_flap_triggered")
    return chaos_engine.inject_payment_flap()


@router.post("/inject/schema-mismatch")
async def inject_schema_mismatch():
    """Simulate Bad Migration Schema Mismatch (missing column 'orders.tax_rate')."""
    logger.warn("chaos_inject_schema_mismatch_triggered")
    return chaos_engine.inject_schema_mismatch()


@router.post("/roulette")
async def chaos_roulette():
    """
    Simulate Random Fault Injection.
    Picks one of the real production incident scenarios at random.
    """
    scenarios = [
        ("POSTGRES_POOL", chaos_engine.inject_postgres_pool),
        ("INVENTORY_TIMEOUT", chaos_engine.inject_timeout),
        ("MEMORY_LEAK", lambda: chaos_engine.inject_memory_leak(30)),
        ("PAYMENT_FLAP", chaos_engine.inject_payment_flap),
        ("SCHEMA_MISMATCH", chaos_engine.inject_schema_mismatch),
    ]
    name, func = random.choice(scenarios)
    logger.warn("chaos_roulette_executed", selected_fault=name)
    state = func()
    return {
        "roulette_outcome": name,
        "message": f"Random crisis fault '{name}' successfully injected into ShopCore microservice!",
        "current_state": state,
    }


@router.post("/reset")
async def reset_chaos():
    """Reset all active chaos faults and clear memory leak buffers."""
    logger.info("chaos_reset_all_triggered")
    return chaos_engine.reset_all()
