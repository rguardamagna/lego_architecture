"""Password hasher interface (port)."""
from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Abstract interface for password hashing."""

    @abstractmethod
    def hash(self, plain: str) -> str:
        """Hash a plain text password."""
        ...

    @abstractmethod
    def verify(self, plain: str, hashed: str) -> bool:
        """Verify a plain text password against a hash."""
        ...
