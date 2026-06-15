"""JWT token service adapter."""
import uuid
import time
from typing import Any

import jwt
from domain.ports.token_service import TokenService
from domain.entities.user import User


class JWTService(TokenService):
    """Implements TokenService using PyJWT with HS256."""

    def __init__(
        self,
        secret: str,
        access_expire_minutes: int = 15,
        refresh_expire_days: int = 7,
    ):
        self._secret = secret
        self._access_expire = access_expire_minutes * 60
        self._refresh_expire = refresh_expire_days * 86400

    def create_access_token(self, user: User) -> str:
        now = int(time.time())
        payload = {
            "sub": str(user.id),
            "email": user.email.value,
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + self._access_expire,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def create_refresh_token(self, user: User) -> tuple[str, uuid.UUID]:
        jti = uuid.uuid4()
        now = int(time.time())
        payload = {
            "sub": str(user.id),
            "jti": str(jti),
            "type": "refresh",
            "iat": now,
            "exp": now + self._refresh_expire,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256"), jti

    def verify_access_token(self, token: str) -> dict[str, Any]:
        return self._verify(token, expected_type="access")

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        return self._verify(token, expected_type="refresh")

    def _verify(self, token: str, expected_type: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                options={"require": ["sub", "type", "iat", "exp"]},
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired") from None
        except jwt.InvalidTokenError as e:
            raise ValueError("Invalid token") from e

        if payload.get("type") != expected_type:
            raise ValueError("Invalid token type")

        return payload
