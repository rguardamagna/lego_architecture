"""JWT verification utilities shared across all services."""
from typing import Any

import jwt as pyjwt


def verify_access_token(token: str, secret: str) -> dict[str, Any]:
    """Verify a JWT access token.

    Args:
        token: The JWT string.
        secret: The HMAC secret key.

    Returns:
        Decoded payload dict with claims.

    Raises:
        ValueError: If token is expired, invalid signature, wrong type,
                    or missing required claims.
    """
    try:
        payload = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
    except pyjwt.ExpiredSignatureError:
        raise ValueError("Token has expired") from None
    except pyjwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    return payload
