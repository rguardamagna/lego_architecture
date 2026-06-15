"""Token service interface (port)."""
from abc import ABC, abstractmethod
from typing import Any
import uuid

from domain.entities.user import User


class TokenService(ABC):
    """Abstract interface for JWT token operations."""

    @abstractmethod
    def create_access_token(self, user: User) -> str:
        """Create a short-lived access token."""
        ...

    @abstractmethod
    def create_refresh_token(self, user: User) -> tuple[str, uuid.UUID]:
        """Create a refresh token. Returns (token, jti)."""
        ...

    @abstractmethod
    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify and decode access token. Returns payload."""
        ...

    @abstractmethod
    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """Verify and decode refresh token. Returns payload."""
        ...
