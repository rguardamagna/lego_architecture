"""OAuth2 provider for Google."""
from typing import Any
from urllib.parse import urlencode
import requests

from domain.ports.oauth_service import OAuthProvider


class GoogleOAuthProvider(OAuthProvider):
    """Implements OAuth2 flow for Google."""

    @property
    def name(self) -> str:
        return "google"

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = urlencode({
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "openid email profile",
            "response_type": "code",
        })
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        # Exchange code for tokens
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        # Decode the ID token to get user info
        from jwt import decode as jwt_decode

        id_token = token_data.get("id_token")
        if not id_token:
            raise ValueError("Google OAuth failed: no id_token received")

        user_info = jwt_decode(id_token, options={"verify_signature": False})

        return {
            "provider": "google",
            "provider_user_id": user_info["sub"],
            "email": user_info.get("email", ""),
            "display_name": user_info.get("name", ""),
            "avatar_url": user_info.get("picture"),
        }
