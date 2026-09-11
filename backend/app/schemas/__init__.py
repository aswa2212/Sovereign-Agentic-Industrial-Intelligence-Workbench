"""Pydantic validation schemas package."""

try:
    from app.schemas.deliverables import (
        DeliverableGenerateRequest,
        DeliverableGenerateResponse,
    )
except ImportError:
    from backend.app.schemas.deliverables import (
        DeliverableGenerateRequest,
        DeliverableGenerateResponse,
    )


__all__ = [
    "DeliverableGenerateRequest",
    "DeliverableGenerateResponse",
]
