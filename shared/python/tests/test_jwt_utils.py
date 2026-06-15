"""Tests for lego_shared.jwt_utils."""
import time
import jwt
import pytest
from lego_shared.jwt_utils import verify_access_token

SECRET = "test-secret"


class TestVerifyAccessToken:
    def test_valid_token_returns_payload(self):
        """Token bien formado y vigente devuelve el payload."""
        now = int(time.time())
        token = jwt.encode({
            "sub": "user-123",
            "type": "access",
            "iat": now,
            "exp": now + 300,
        }, SECRET, algorithm="HS256")

        payload = verify_access_token(token, SECRET)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_expired_token_raises_error(self):
        """Token expirado debe levantar ValueError."""
        now = int(time.time())
        token = jwt.encode({
            "sub": "user-123",
            "type": "access",
            "iat": now - 600,
            "exp": now - 300,
        }, SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="expired"):
            verify_access_token(token, SECRET)

    def test_invalid_signature_raises_error(self):
        """Token con firma inválida debe levantar ValueError."""
        now = int(time.time())
        token = jwt.encode({
            "sub": "user-123",
            "type": "access",
            "iat": now,
            "exp": now + 300,
        }, "wrong-secret", algorithm="HS256")

        with pytest.raises(ValueError, match="Invalid"):
            verify_access_token(token, SECRET)

    def test_wrong_token_type_raises_error(self):
        """Token de tipo refresh no pasa como access."""
        now = int(time.time())
        token = jwt.encode({
            "sub": "user-123",
            "type": "refresh",
            "iat": now,
            "exp": now + 300,
        }, SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="token type"):
            verify_access_token(token, SECRET)

    def test_missing_required_claims_raises_error(self):
        """Token sin claims requeridos debe fallar."""
        now = int(time.time())
        token = jwt.encode({
            "sub": "user-123",
            "type": "access",
            # Missing iat and exp
        }, SECRET, algorithm="HS256")

        with pytest.raises(ValueError):
            verify_access_token(token, SECRET)

    def test_malformed_token_raises_error(self):
        """String que no es JWT debe levantar ValueError."""
        with pytest.raises(ValueError):
            verify_access_token("not-a-jwt-token", SECRET)
