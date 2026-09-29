from typing import Any, Literal

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.chaos.state import chaos_engine

logger = structlog.get_logger()
router = APIRouter(prefix="/operations", tags=["Operations & Runtime Mitigation (OpsMesh Target)"])


class MitigationRequest(BaseModel):
    action_type: Literal[
        "DATABASE_CONNECTION_SCALE",
        "DATABASE_TERMINATE_BACKENDS",
        "POD_ROLLOUT_RESTART",
        "MEMORY_GC_FLUSH",
        "CIRCUIT_BREAKER_ACTIVATE",
        "SCHEMA_HOTFIX",
        "ALL",
    ] = Field(
        ...,
        description="Standardized OpsMesh Tier 1 runtime action type",
        examples=["DATABASE_CONNECTION_SCALE"],
    )
    requester: str = Field(
        default="OpsMesh-Autonomous-Agent",
        description="Actor requesting the mitigation (OpsMesh Agent or SRE on-call)",
    )
    details: str = Field(
        default="",
        description="Technical justification or diagnostic notes",
    )


class MitigationResponse(BaseModel):
    status: Literal["SUCCESS", "PARTIAL", "FAILED"]
    action_type: str
    actions_applied: list[str]
    time_taken_ms: float
    current_state: dict[str, Any]
    message: str


@router.post("/mitigate", response_model=MitigationResponse)
async def apply_runtime_mitigation(payload: MitigationRequest):
    """
    Standardized OpsMesh Tier 1 Operational Mitigation Endpoint.
    Executed by OpsMesh in < 5 seconds following SRE approval (or automated policy)
    to immediately stop the bleeding, restore SLOs, and buy time for Tier 2 GitOps PR.
    """
    logger.info(
        "runtime_mitigation_requested",
        action_type=payload.action_type,
        requester=payload.requester,
        details=payload.details,
    )

    result = chaos_engine.mitigate(payload.action_type, payload.details)

    logger.info(
        "runtime_mitigation_applied_successfully",
        action_type=payload.action_type,
        actions_applied=result["actions_applied"],
    )

    return MitigationResponse(
        status="SUCCESS",
        action_type=payload.action_type,
        actions_applied=result["actions_applied"],
        time_taken_ms=12.4,
        current_state=result["current_state"],
        message=f"Runtime mitigation '{payload.action_type}' applied in 12.4ms. System stabilizing.",
    )
