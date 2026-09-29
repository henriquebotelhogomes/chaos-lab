import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from scalar_fastapi import get_scalar_api_reference

from src.api.routes import router as ecommerce_router
from src.chaos.mitigate import router as mitigate_router
from src.chaos.routes import router as chaos_router
from src.chaos.state import chaos_engine
from src.core.config import settings
from src.core.logging import setup_logging

setup_logging()
logger = structlog.get_logger()

# Optional Datadog auto-tracing initialization
if os.getenv("DD_TRACE_ENABLED", "false").lower() in ("true", "1", "yes"):
    try:
        from ddtrace import patch_all

        patch_all(fastapi=True)
        logger.info("datadog_apm_patch_all_initialized", service=settings.dd_service)
    except Exception as e:
        logger.warning("datadog_apm_initialization_skipped", reason=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "chaos_lab_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )
    yield
    logger.info("chaos_lab_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce microservice (ShopCore API) instrumented with Datadog APM and real fault injection for OpsMesh.",
    lifespan=lifespan,
    docs_url=None,  # Disabled classic Swagger UI in favor of Scalar
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(ecommerce_router)
app.include_router(chaos_router)
app.include_router(mitigate_router)

# Templates directory for interactive UI
TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard(request: Request):
    """Interactive Chaos Engineering Dashboard UI."""
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "opsmesh_url": settings.opsmesh_url,
        },
    )


@app.get("/health", tags=["Health & Telemetry"])
async def health_check():
    """Service health and Datadog APM readiness."""
    snapshot = chaos_engine.get_snapshot()
    is_healthy = snapshot["is_healthy"]

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "HEALTHY" if is_healthy else "DEGRADED",
            "service": settings.dd_service,
            "version": settings.app_version,
            "env": settings.app_env,
            "datadog_apm": {
                "enabled": os.getenv("DD_TRACE_ENABLED", "false").lower() in ("true", "1", "yes"),
                "service": settings.dd_service,
                "agent_host": settings.dd_agent_host,
            },
            "chaos_status": snapshot,
        },
    )


@app.get("/docs", include_in_schema=False)
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    """State-of-the-art interactive API documentation powered by Scalar."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=f"{settings.app_name} — Scalar Interactive API Reference",
    )
