"""OAuth provider interface (port)."""
from abc import ABC, abstractmethod
from typing import Any


class OAuthProvider(ABC):
    """Abstract interface for OAuth2 providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'google', 'github')."""
        ...

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generate the OAuth authorization URL to redirect the user to."""
        ...

    @abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for user info.

        Returns:
            dict with keys: email, provider_user_id, display_name, avatar_url
        """
        ...
