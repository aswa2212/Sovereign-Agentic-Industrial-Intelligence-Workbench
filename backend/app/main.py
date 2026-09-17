"""
SIH26117 — Sovereign On-Premise Agentic AI Workbench for MRPL
FastAPI Application Entry Point & Central API Gateway
"""

import sys
from pathlib import Path

# Ensure project root and backend are reliably on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_PROJECT_ROOT), str(_BACKEND_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from app.api.v1.router import api_v1_router
    from app.core.config import get_settings
    from app.core.errors import register_error_handlers
    from app.core.logging import get_logger, setup_logging
    from app.core.middleware import RequestContextMiddleware
except ImportError:
    from backend.app.api.v1.router import api_v1_router
    from backend.app.core.config import get_settings
    from backend.app.core.errors import register_error_handlers
    from backend.app.core.logging import get_logger, setup_logging
    from backend.app.core.middleware import RequestContextMiddleware

settings = get_settings()

# Initialize structured local logging (zero remote telemetry)
setup_logging(settings.log_level)
logger = get_logger(__name__)

# Create the foundational FastAPI Gateway
app = FastAPI(
    title=settings.app_name,
    description=(
        "Air-Gapped Sovereign Agentic AI Gateway for Mangalore Refinery and "
        "Petrochemicals Limited (MRPL). Exclusively orchestrates local models "
        "and tools with zero outbound external telemetry."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register centralized error handling (consistent JSON envelopes)
register_error_handlers(app)

# Register request tracking and latency middleware
app.add_middleware(RequestContextMiddleware)

# Register CORS middleware for local UI development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-Request-ID"],
)

# Mount API v1 router
app.include_router(api_v1_router)


@app.get("/", tags=["Gateway"])
async def root():
    """Root entry point providing high-level workbench information."""
    return {
        "system": settings.app_name,
        "sponsor": "Mangalore Refinery and Petrochemicals Limited (MRPL)",
        "mode": "Sovereign / Air-Gapped",
        "air_gapped_mode": settings.air_gapped_mode,
        "version": settings.app_version,
        "status": "online",
        "timestamp": time.time(),
        "documentation": "/docs",
    }


@app.get("/health", tags=["Gateway"])
async def legacy_health():
    """Root health check alias redirecting to standard health schema."""
    return {
        "status": "ok",
        "service": f"{settings.app_name} Gateway",
        "version": settings.app_version,
        "air_gapped_mode": settings.air_gapped_mode,
    }


@app.on_event("startup")
async def on_startup():
    """Log gateway startup state."""
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version} "
        f"[Hardware Tier: {settings.hardware_tier}] "
        f"[Air-Gap: {settings.air_gapped_mode}]"
    )
