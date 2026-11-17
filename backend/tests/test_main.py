"""
Integration tests for FastAPI endpoints, Swagger docs, and database session dependency.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import get_db

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns application information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "VisualGuard AI Backend"
    assert data["version"] == "1.0.0"
    assert data["status"] == "online"
    assert data["docs_url"] == "/docs"
    assert data["redoc_url"] == "/redoc"
    assert data["environment"] == settings.ENVIRONMENT


def test_health_endpoint():
    """Verify GET /health returns server health status and PostgreSQL diagnostic details."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert data["app_name"] == "VisualGuard AI Backend"
    assert data["version"] == "1.0.0"
    assert "database" in data
    assert "connected" in data["database"]
    assert "details" in data["database"]
    assert isinstance(data["database"]["connected"], bool)


def test_swagger_docs():
    """Verify GET /docs returns the Swagger UI interface."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "swagger-ui" in response.text.lower()


def test_redoc_docs():
    """Verify GET /redoc returns the ReDoc interface."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "redoc" in response.text.lower()


def test_openapi_json():
    """Verify OpenAPI schema configuration matches metadata."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "VisualGuard AI Backend"
    assert schema["info"]["version"] == "1.0.0"


def test_get_db_dependency():
    """Verify that the get_db generator yields a session and closes properly."""
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    # Closing the generator invokes the finally block
    with pytest.raises(StopIteration):
        next(db_gen)


def test_cors_headers_and_preflight():
    """Verify CORS preflight and response headers allow frontend interaction."""
    # Preflight OPTIONS request
    preflight = client.options(
        "/api/videos",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert preflight.headers.get("access-control-allow-credentials") == "true"
    assert "POST" in preflight.headers.get("access-control-allow-methods", "")

    # Normal GET with Origin header
    get_res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert get_res.status_code == 200
    assert get_res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert get_res.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-expose-headers" in get_res.headers

