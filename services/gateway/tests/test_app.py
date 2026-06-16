"""Tests for gateway app factory."""
import json

import pytest


@pytest.fixture
def client(monkeypatch):
    """Create a test client with predefined routes."""
    monkeypatch.setenv("GATEWAY_ROUTE_AUTH", "http://auth:8000/auth")
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "test-secret")
    monkeypatch.setenv("GATEWAY_JWT_PREVERIFY", "true")

    from gateway.app import create_app
    app = create_app()
    with app.test_client() as client:
        yield client


class TestAppFactory:
    def test_health_endpoint(self, client):
        """/health debe devolver 200 con status healthy."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "healthy"
        assert data["service"] == "gateway"

    def test_health_returns_json(self, client):
        """/health debe tener Content-Type application/json."""
        resp = client.get("/health")
        assert resp.content_type == "application/json"

    def test_unknown_route_returns_404(self, client):
        """Ruta sin match debe devolver 404."""
        resp = client.get("/api/v1/unknown/test")
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert "error" in data

    def test_known_route_returns_502_when_upstream_down(self, client):
        """Ruta conocida pero upstream caído debe devolver 502."""
        # Auth route is defined but upstream not running
        resp = client.get("/api/v1/auth/health")
        assert resp.status_code == 502
        data = json.loads(resp.data)
        assert data["error"] == "bad_gateway"

    def test_cors_headers_on_get(self, client):
        """GET debe incluir Access-Control-Allow-Origin."""
        resp = client.get("/health")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_preflight(self, client):
        """OPTIONS /health debe devolver 204 con CORS headers."""
        resp = client.options("/health")
        assert resp.status_code == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
