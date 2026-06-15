"""Tests for gateway router."""
import pytest
from gateway.router.routes import init_routes, find_route, ROUTE_PREFIX_MAP


class TestRouter:
    def setup_method(self):
        """Limpiar rutas antes de cada test."""
        ROUTE_PREFIX_MAP.clear()

    def test_init_routes_populates_map(self):
        """init_routes con route_map poblado debe llenar ROUTE_PREFIX_MAP."""
        init_routes({"AUTH": "http://auth:8000", "USER": "http://user:8000"})
        assert ROUTE_PREFIX_MAP["/api/v1/auth/"] == "http://auth:8000"
        assert ROUTE_PREFIX_MAP["/api/v1/user/"] == "http://user:8000"

    def test_init_routes_empty(self):
        """init_routes con map vacío debe dejar ROUTE_PREFIX_MAP vacío."""
        init_routes({})
        assert ROUTE_PREFIX_MAP == {}

    def test_find_route_matches_exact_prefix(self):
        """find_route debe matchear prefijo exacto."""
        init_routes({"AUTH": "http://auth:8000"})
        target, remaining = find_route("/api/v1/auth/register")
        assert target == "http://auth:8000"
        assert remaining == "/register"

    def test_find_route_no_slash_after_prefix(self):
        """find_route funciona sin slash después del prefix."""
        init_routes({"AUTH": "http://auth:8000"})
        target, remaining = find_route("/api/v1/auth")
        assert target == "http://auth:8000"
        assert remaining == ""

    def test_find_route_no_match_returns_none(self):
        """find_route sin match debe devolver None."""
        init_routes({"AUTH": "http://auth:8000"})
        assert find_route("/api/v1/unknown/foo") is None

    def test_find_route_longest_prefix_wins(self):
        """Prefijo más específico debe ganar sobre uno genérico."""
        init_routes({
            "AUTH": "http://auth:8000",
            "AUTH-ADMIN": "http://auth-admin:8000",
        })
        ROUTE_PREFIX_MAP["/api/v1/auth-admin/"] = "http://auth-admin:8000"

        target, remaining = find_route("/api/v1/auth-admin/users")
        assert target == "http://auth-admin:8000"
        assert remaining == "/users"

    def test_find_route_health_not_in_routes(self):
        """/health no está en las rutas de proxy."""
        init_routes({"AUTH": "http://auth:8000"})
        assert find_route("/health") is None

    def test_find_route_empty_path(self):
        """Path vacío debe devolver None."""
        init_routes({"AUTH": "http://auth:8000"})
        assert find_route("") is None

    def test_remaining_path_preserves_query_string(self):
        """Query string debe preservarse en remaining."""
        init_routes({"USER": "http://user:8000"})
        _, remaining = find_route("/api/v1/user/me?include=profile")
        assert remaining == "/me?include=profile"
