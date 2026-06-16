"""Tests for gateway config."""
import os
import pytest
from gateway.config import Settings


class TestSettings:
    def test_default_values(self):
        """Defaults should be sane."""
        s = Settings()
        assert s.port == 8080
        assert s.jwt_preverify is True
        assert s.cors_origins == "*"
        assert s.log_level == "INFO"
        assert s.upstream_timeout == 30

    def test_route_map_with_envs(self, monkeypatch):
        """GATEWAY_ROUTE_AUTH and friends should populate route_map."""
        monkeypatch.setenv("GATEWAY_ROUTE_AUTH", "http://auth:8000/auth")
        monkeypatch.setenv("GATEWAY_ROUTE_USER", "http://user:8000")
        s = Settings()
        assert s.route_map["AUTH"] == "http://auth:8000/auth"
        assert s.route_map["USER"] == "http://user:8000"

    def test_route_map_empty_without_envs(self):
        """Without GATEWAY_ROUTE_* envs, route_map should be empty."""
        s = Settings()
        assert s.route_map == {}

    def test_route_map_prefix_derivation(self, monkeypatch):
        """Keys like AUTH should derive prefix /api/v1/auth/."""
        monkeypatch.setenv("GATEWAY_ROUTE_AUTH", "http://auth:8000/auth")
        s = Settings()
        routes = s.route_map
        prefix = f"/api/v1/{list(routes.keys())[0].lower()}/"
        assert prefix == "/api/v1/auth/"
        assert routes["AUTH"] == "http://auth:8000/auth"

    def test_custom_env_prefix(self, monkeypatch):
        """route_map should only include GATEWAY_ROUTE_* prefixed vars."""
        monkeypatch.setenv("GATEWAY_ROUTE_AUTH", "http://auth:8000/auth")
        monkeypatch.setenv("GATEWAY_ROUTE_CUSTOM", "/api/v2/notif|http://notif:8000")
        monkeypatch.setenv("GATEWAY_UNRELATED", "http://x:8000")
        s = Settings()
        assert "UNRELATED" not in s.route_map
        assert s.route_map.get("CUSTOM") is not None
