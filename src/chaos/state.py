import threading
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ChaosIncidentEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_type: str
    details: str


class ChaosEngineState:
    """Thread-safe state manager for active chaos faults and runtime mitigations."""

    def __init__(self):
        self._lock = threading.RLock()
        self.postgres_pool_exhausted: bool = False
        self.inventory_timeout: bool = False
        self.memory_leak: bool = False
        self.payment_gateway_flapping: bool = False
        self.schema_mismatch: bool = False

        # Operational buffers and counters
        self.leaked_chunks: list[bytearray] = []
        self.simulated_active_conns: int = 2
        self.simulated_max_conns: int = 10
        self.history: list[ChaosIncidentEvent] = []
        self.total_faults_injected: int = 0
        self.total_mitigations_applied: int = 0

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "postgres_pool_exhausted": self.postgres_pool_exhausted,
                "inventory_timeout": self.inventory_timeout,
                "memory_leak": self.memory_leak,
                "memory_leak_mb": len(self.leaked_chunks) * 5,  # 5MB per chunk
                "payment_gateway_flapping": self.payment_gateway_flapping,
                "schema_mismatch": self.schema_mismatch,
                "simulated_active_conns": self.simulated_active_conns,
                "simulated_max_conns": self.simulated_max_conns,
                "total_faults_injected": self.total_faults_injected,
                "total_mitigations_applied": self.total_mitigations_applied,
                "is_healthy": not (
                    self.postgres_pool_exhausted
                    or self.inventory_timeout
                    or self.memory_leak
                    or self.payment_gateway_flapping
                    or self.schema_mismatch
                ),
                "recent_events": [e.model_dump() for e in self.history[-10:]],
            }

    def inject_postgres_pool(self) -> dict[str, Any]:
        with self._lock:
            self.postgres_pool_exhausted = True
            self.simulated_active_conns = 15  # Overflow beyond max 10
            self.total_faults_injected += 1
            self.history.append(
                ChaosIncidentEvent(
                    event_type="FAULT_INJECTED",
                    details="PostgreSQL Connection Pool Exhausted (15/10 active connections).",
                )
            )
            return self.get_snapshot()

    def inject_timeout(self) -> dict[str, Any]:
        with self._lock:
            self.inventory_timeout = True
            self.total_faults_injected += 1
            self.history.append(
                ChaosIncidentEvent(
                    event_type="FAULT_INJECTED",
                    details="Inventory Cascade Timeout Injected (Forced 15s Latency -> 504 Gateway Timeout).",
                )
            )
            return self.get_snapshot()

    def inject_memory_leak(self, megabytes: int = 25) -> dict[str, Any]:
        with self._lock:
            self.memory_leak = True
            self.total_faults_injected += 1
            # Allocate 5MB blocks to simulate uncollected tensor/object allocations
            num_chunks = max(1, megabytes // 5)
            for _ in range(num_chunks):
                self.leaked_chunks.append(bytearray(5 * 1024 * 1024))
            self.history.append(
                ChaosIncidentEvent(
                    event_type="FAULT_INJECTED",
                    details=f"Unbounded Memory Leak Injected (+{len(self.leaked_chunks) * 5}MB RAM allocated without GC).",
                )
            )
            return self.get_snapshot()

    def inject_payment_flap(self) -> dict[str, Any]:
        with self._lock:
            self.payment_gateway_flapping = True
            self.total_faults_injected += 1
            self.history.append(
                ChaosIncidentEvent(
                    event_type="FAULT_INJECTED",
                    details="External Payment Gateway Flapping (Simulating Stripe/Adyen 500 Network Failures).",
                )
            )
            return self.get_snapshot()

    def inject_schema_mismatch(self) -> dict[str, Any]:
        with self._lock:
            self.schema_mismatch = True
            self.total_faults_injected += 1
            self.history.append(
                ChaosIncidentEvent(
                    event_type="FAULT_INJECTED",
                    details="Database Schema Mismatch (Simulating missing column 'tax_rate' in table 'orders').",
                )
            )
            return self.get_snapshot()

    def reset_all(self) -> dict[str, Any]:
        with self._lock:
            self.postgres_pool_exhausted = False
            self.inventory_timeout = False
            self.memory_leak = False
            self.payment_gateway_flapping = False
            self.schema_mismatch = False
            self.leaked_chunks.clear()
            self.simulated_active_conns = 2
            self.history.append(
                ChaosIncidentEvent(
                    event_type="MANUAL_RESET",
                    details="Manual full reset applied to all chaos faults.",
                )
            )
            return self.get_snapshot()

    def mitigate(self, action_type: str, details: str = "") -> dict[str, Any]:
        with self._lock:
            applied = []
            if action_type in ["DATABASE_CONNECTION_SCALE", "DATABASE_TERMINATE_BACKENDS", "ALL"]:
                self.postgres_pool_exhausted = False
                self.simulated_active_conns = 2
                applied.append("Reset DB connection pool and terminated idle backends")

            if action_type in ["CIRCUIT_BREAKER_ACTIVATE", "ALL"]:
                self.inventory_timeout = False
                self.payment_gateway_flapping = False
                applied.append("Activated circuit breakers for inventory and payment downstreams")

            if action_type in ["POD_ROLLOUT_RESTART", "MEMORY_GC_FLUSH", "ALL"]:
                self.memory_leak = False
                self.leaked_chunks.clear()
                applied.append("Forced garbage collection flush and cleared memory buffers")

            if action_type in ["SCHEMA_HOTFIX", "ALL"]:
                self.schema_mismatch = False
                applied.append("Applied hotfix migration to add missing columns in orders table")

            self.total_mitigations_applied += 1
            summary = "; ".join(applied) if applied else f"Mitigation executed: {action_type}"
            self.history.append(
                ChaosIncidentEvent(
                    event_type="RUNTIME_MITIGATION_APPLIED",
                    details=f"OpsMesh Nível 1 Mitigação [{action_type}]: {summary}. {details}".strip(),
                )
            )
            return {
                "status": "MITIGATED",
                "action_type": action_type,
                "actions_applied": applied,
                "current_state": self.get_snapshot(),
            }


chaos_engine = ChaosEngineState()
