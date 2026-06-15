"""Tests para adapters reales de password y token."""
import uuid
import time
from datetime import datetime, timedelta, timezone

import pytest

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.ports.password_hasher import PasswordHasher
from domain.ports.token_service import TokenService
from adapters.password.bcrypt_hasher import BCryptPasswordHasher
from adapters.token.jwt_service import JWTService


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def hasher() -> PasswordHasher:
    return BCryptPasswordHasher()


@pytest.fixture
def token_svc() -> JWTService:
    return JWTService(
        secret="test-secret-key-for-testing-only",
        access_expire_minutes=15,
        refresh_expire_days=7,
    )


@pytest.fixture
def sample_user() -> User:
    return User(
        id=uuid.uuid4(),
        email=Email("test@example.com"),
        password_hash="hashed_placeholder",
        display_name="Test User",
        avatar_url=None,
        oauth_links=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ── Tests: BCryptPasswordHasher ─────────────────────────────────


class TestBCryptHasher:
    def test_implements_interface(self, hasher):
        assert isinstance(hasher, PasswordHasher)

    def test_hash_returns_string(self, hasher):
        hashed = hasher.hash("Str0ng!Pass")
        assert isinstance(hashed, str)
        assert len(hashed) > 20

    def test_hash_is_different_each_time(self, hasher):
        h1 = hasher.hash("Str0ng!Pass")
        h2 = hasher.hash("Str0ng!Pass")
        assert h1 != h2  # bcrypt saltea

    def test_verify_correct(self, hasher):
        hashed = hasher.hash("Str0ng!Pass")
        assert hasher.verify("Str0ng!Pass", hashed) is True

    def test_verify_wrong(self, hasher):
        hashed = hasher.hash("Str0ng!Pass")
        assert hasher.verify("WrongPass1!", hashed) is False

    def test_verify_empty(self, hasher):
        hashed = hasher.hash("Str0ng!Pass")
        assert hasher.verify("", hashed) is False


# ── Tests: JWTService ────────────────────────────────────────────


class TestJWTService:
    def test_implements_interface(self, token_svc):
        assert isinstance(token_svc, TokenService)

    def test_create_access_token_returns_string(self, token_svc, sample_user):
        token = token_svc.create_access_token(sample_user)
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # header.payload.signature

    def test_create_refresh_token_returns_token_and_jti(self, token_svc, sample_user):
        token, jti = token_svc.create_refresh_token(sample_user)
        assert isinstance(token, str)
        assert isinstance(jti, uuid.UUID)
        assert len(token.split(".")) == 3

    def test_verify_access_token_valid(self, token_svc, sample_user):
        token = token_svc.create_access_token(sample_user)
        payload = token_svc.verify_access_token(token)
        assert payload["sub"] == str(sample_user.id)
        assert payload["email"] == sample_user.email.value
        assert payload["type"] == "access"

    def test_verify_refresh_token_valid(self, token_svc, sample_user):
        token, jti = token_svc.create_refresh_token(sample_user)
        payload = token_svc.verify_refresh_token(token)
        assert payload["sub"] == str(sample_user.id)
        assert payload["type"] == "refresh"
        assert uuid.UUID(payload["jti"]) == jti

    def test_verify_invalid_token_raises(self, token_svc):
        with pytest.raises(ValueError, match="Invalid token"):
            token_svc.verify_access_token("invalid.token.here")

    def test_verify_wrong_secret_raises(self, token_svc, sample_user):
        token = token_svc.create_access_token(sample_user)
        other_svc = JWTService(
            secret="different-secret-key-here",
        )
        with pytest.raises(ValueError, match="Invalid token"):
            other_svc.verify_access_token(token)

    def test_verify_expired_token_raises(self, sample_user):
        svc = JWTService(secret="test-secret", access_expire_minutes=0)  # expires immediately
        token = svc.create_access_token(sample_user)
        time.sleep(1)
        with pytest.raises(ValueError, match="expired"):
            svc.verify_access_token(token)

    def test_access_token_has_proper_expiry(self, token_svc, sample_user):
        token = token_svc.create_access_token(sample_user)
        payload = token_svc.verify_access_token(token)
        assert "exp" in payload
        assert "iat" in payload
        # Should be ~15 minutes from now
        expected_exp = int(time.time()) + 14 * 60
        assert abs(payload["exp"] - expected_exp) < 120  # within 2 minutes
