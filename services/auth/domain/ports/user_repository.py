"""User repository interface (port)."""
from abc import ABC, abstractmethod
from typing import Optional
import uuid

from domain.entities.user import User
from domain.value_objects.email import Email


class UserRepository(ABC):
    """Abstract interface for user persistence."""

    @abstractmethod
    def save(self, user: User) -> User:
        """Persist a new user. Raises on duplicate email."""
        ...

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user."""
        ...

    @abstractmethod
    def find_by_email(self, email: Email) -> Optional[User]:
        """Find user by email. Returns None if not found."""
        ...

    @abstractmethod
    def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Find user by ID. Returns None if not found."""
        ...

    @abstractmethod
    def find_by_oauth(self, provider: str, provider_user_id: str) -> Optional[User]:
        """Find user by OAuth provider + provider_user_id. Returns None if not found."""
        ...

    @abstractmethod
    def save_refresh_token(self, jti: uuid.UUID, user_id: uuid.UUID, expires_at) -> None:
        """Persist a refresh token."""
        ...

    @abstractmethod
    def find_refresh_token(self, jti: uuid.UUID) -> Optional[dict]:
        """Find refresh token. Returns dict or None."""
        ...

    @abstractmethod
    def revoke_refresh_token(self, jti: uuid.UUID) -> None:
        """Mark refresh token as revoked."""
        ...

    @abstractmethod
    def add_oauth_link(self, user_id: uuid.UUID, provider: str, provider_user_id: str) -> None:
        """Add OAuth link to a user."""
        ...
