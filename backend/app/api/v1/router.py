"""
SIH26117 — API v1 Master Router
Assembles sub-routers for health, system, models, task router, and future service routes.
"""

from fastapi import APIRouter

try:
    from app.api.v1.endpoints.agent import router as agent_router
    from app.api.v1.endpoints.files import router as files_router
    from app.api.v1.endpoints.health import router as health_router
    from app.api.v1.endpoints.models import router as models_router
    from app.api.v1.endpoints.rag import router as rag_router
    from app.api.v1.endpoints.router import router as task_router_router
    from app.api.v1.endpoints.sandbox import router as sandbox_router
    from app.api.v1.endpoints.system import router as system_router
    from app.api.v1.endpoints.vision import router as vision_router
except ImportError:
    from backend.app.api.v1.endpoints.agent import router as agent_router
    from backend.app.api.v1.endpoints.files import router as files_router
    from backend.app.api.v1.endpoints.health import router as health_router
    from backend.app.api.v1.endpoints.models import router as models_router
    from backend.app.api.v1.endpoints.rag import router as rag_router
    from backend.app.api.v1.endpoints.router import router as task_router_router
    from backend.app.api.v1.endpoints.sandbox import router as sandbox_router
    from backend.app.api.v1.endpoints.system import router as system_router
    from backend.app.api.v1.endpoints.vision import router as vision_router

api_v1_router = APIRouter(prefix="/api/v1")

# Phase 1 — Foundation endpoints
api_v1_router.include_router(health_router)
api_v1_router.include_router(system_router)

# Phase 2 — Local Model Manager endpoints
api_v1_router.include_router(models_router)

# Phase 3 — Task Router endpoints
api_v1_router.include_router(task_router_router)

# Phase 4 — Document Ingestion endpoints
api_v1_router.include_router(files_router)

# Phase 5 — OCR & Vision Engine endpoints
api_v1_router.include_router(vision_router)

# Phase 6 — Sovereign Knowledge & RAG Layer endpoints
api_v1_router.include_router(rag_router)

# Phase 7 — Agent State Machine & Orchestrator endpoints
api_v1_router.include_router(agent_router)

# Phase 8 — Sandboxed Tool Execution endpoints
api_v1_router.include_router(sandbox_router)
