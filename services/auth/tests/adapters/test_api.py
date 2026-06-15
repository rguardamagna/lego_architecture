"""Tests para la API Flask."""
import uuid
import json
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthProvider, OAuthLink
from adapters.repository.models import Base
from adapters.repository.user_repository import PostgresUserRepository
from adapters.password.bcrypt_hasher import BCryptPasswordHasher
from adapters.token.jwt_service import JWTService
from adapters.flask.app import create_app
from adapters.flask.routes import auth_bp


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def repo(engine):
    return PostgresUserRepository(engine)


@pytest.fixture
def hasher():
    return BCryptPasswordHasher()


@pytest.fixture
def token_svc():
    return JWTService(secret="test-secret-key-for-testing-at-least-32-bytes!")


@pytest.fixture
def app(repo, hasher, token_svc):
    app = create_app(
        repo=repo,
        hasher=hasher,
        token_service=token_svc,
        jwt_secret="test-secret-key-for-testing-at-least-32-bytes!",
        cors_origins="*",
    )
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_user(client):
    """Register a user and return (email, password)."""
    resp = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "Secure1!Pass", "display_name": "Alice"},
    )
    data = resp.get_json()
    return {
        "email": "alice@example.com",
        "password": "Secure1!Pass",
        "user_id": data["user"]["id"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


# ── Health ─────────────────────────────────────────────────────


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth"


# ── Register ──────────────────────────────────────────────────


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "bob@example.com", "password": "Secure1!Pass", "display_name": "Bob"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "bob@example.com"
        assert data["user"]["display_name"] == "Bob"

    def test_register_duplicate(self, client):
        client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "Secure1!Pass", "display_name": "Dup"},
        )
        resp = client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "Secure2!Pass", "display_name": "Dup2"},
        )
        assert resp.status_code == 409

    def test_register_weak_password(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "weak@example.com", "password": "short", "display_name": "Weak"},
        )
        assert resp.status_code == 400

    def test_register_invalid_email(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "Secure1!Pass", "display_name": "Bad"},
        )
        assert resp.status_code == 400

    def test_register_missing_fields(self, client):
        resp = client.post("/auth/register", json={"email": "test@example.com"})
        assert resp.status_code == 400


# ── Login ─────────────────────────────────────────────────────


class TestLogin:
    def test_login_success(self, client, registered_user):
        resp = client.post(
            "/auth/login",
            json={"email": registered_user["email"], "password": registered_user["password"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post(
            "/auth/login",
            json={"email": registered_user["email"], "password": "WrongPass1!"},
        )
        assert resp.status_code == 401

    def test_login_user_not_found(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "Secure1!Pass"},
        )
        assert resp.status_code == 401


# ── Auth/Me ────────────────────────────────────────────────────


class TestMe:
    def test_get_me_with_token(self, client, registered_user):
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["email"] == registered_user["email"]
        assert data["id"] == registered_user["user_id"]

    def test_get_me_no_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


# ── Refresh ──────────────────────────────────────────────────


class TestRefresh:
    def test_refresh_success(self, client, registered_user):
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert "access_token" in data
        # Tokens should be different (rotation)
        assert data["access_token"] != registered_user["access_token"]
        # Verify the new token is valid
        from adapters.token.jwt_service import JWTService
        svc = JWTService(secret="test-secret-key-for-testing-at-least-32-bytes!")
        payload = svc.verify_access_token(data["access_token"])
        assert payload["sub"] == registered_user["user_id"]

    def test_refresh_invalid_token(self, client):
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────


class TestLogout:
    def test_logout_success(self, client, registered_user):
        resp = client.post(
            "/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 204

    def test_logout_then_refresh_revoked(self, client, registered_user):
        client.post(
            "/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        resp = client.post(
            "/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert resp.status_code == 401


# ── Error format ─────────────────────────────────────────────


class TestErrorFormat:
    def test_error_has_standard_format(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401
        data = resp.get_json()
        assert "error" in data
        assert "message" in data


# ── OAuth routes ──────────────────────────────────────────────


class TestOAuthRoutes:
    def test_oauth_login_unsupported_provider(self, client):
        resp = client.get("/auth/oauth/twitter/login")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "invalid_provider"

    def test_oauth_login_requires_redirect_uri(self, client, app):
        # Provide a valid provider in app config
        from adapters.oauth.github import GitHubOAuthProvider
        from adapters.oauth.google import GoogleOAuthProvider

        app.config["oauth_providers"] = {
            "github": GitHubOAuthProvider("test-id", "test-secret"),
        }
        auth_bp.oauth_providers = app.config["oauth_providers"]

        resp = client.get("/auth/oauth/github/login?redirect_uri=http://localhost:5173/callback")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "authorization_url" in data
        assert "github.com" in data["authorization_url"]
        assert "state" in data

    def test_oauth_callback_missing_code(self, client):
        resp = client.get("/auth/oauth/google/callback")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "missing_code"
