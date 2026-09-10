"""
SIH26117 — Phase 1 Gateway API Unit Tests
Verifies health, system status, capabilities, error envelopes, and request ID tracking.
All tests execute purely offline without requiring Ollama, GPU, or external networks.
"""

import pytest
from fastapi.testclient import TestClient

try:
    from app.main import app
except ImportError:
    from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that root endpoint returns operational metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["mode"] == "Sovereign / Air-Gapped"
    assert data["air_gapped_mode"] is True
    assert "version" in data


def test_root_health_endpoint():
    """Verify legacy /health endpoint alias."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["air_gapped_mode"] is True


def test_api_v1_health_endpoint():
    """Verify /api/v1/health returns structured health schema."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "SIH26117" in data["service"]
    assert data["air_gapped_mode"] is True
    assert "version" in data


def test_api_v1_system_status():
    """Verify /api/v1/system/status reports accurate operational status and module states."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["air_gapped_mode"] is True
    assert data["inference_provider"] == "ollama"
    assert "modules" in data

    # All unbuilt modules must be explicitly reported as not_initialized
    modules = data["modules"]
    assert modules["router"] == "not_initialized"
    assert modules["agent"] == "not_initialized"
    assert modules["model_manager"] == "not_initialized"
    assert modules["rag"] == "not_initialized"
    assert modules["vision"] == "not_initialized"
    assert modules["sandbox"] == "not_initialized"
    assert modules["deliverables"] == "not_initialized"


def test_api_v1_system_capabilities():
    """Verify /api/v1/system/capabilities returns planned MVP capabilities."""
    response = client.get("/api/v1/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert "implementation_status" in data

    caps = data["capabilities"]
    assert caps["routing"] is True
    assert caps["agentic_execution"] is True
    assert caps["rag"] is True
    assert caps["multimodal_ingestion"] is True
    assert caps["vision"] is True
    assert caps["sandbox_execution"] is True
    assert caps["office_generation"] is True
    assert caps["air_gap_monitoring"] is True

    statuses = data["implementation_status"]
    assert statuses["routing"] == "planned"
    assert statuses["agentic_execution"] == "planned"


def test_error_envelope_for_not_found():
    """Verify centralized error handler returns structured JSON on 404."""
    response = client.get("/api/v1/nonexistent_endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]


def test_request_id_middleware_header():
    """Verify X-Request-ID header is generated and injected into response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_openapi_documentation_endpoints():
    """Verify that /docs and /openapi.json are accessible."""
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    spec = openapi_response.json()
    assert spec["info"]["title"] == "SIH26117 Sovereign AI Workbench"
