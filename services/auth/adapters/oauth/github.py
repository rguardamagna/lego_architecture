"""OAuth2 provider for GitHub."""
from typing import Any
from urllib.parse import urlencode
import requests

from domain.ports.oauth_service import OAuthProvider


class GitHubOAuthProvider(OAuthProvider):
    """Implements OAuth2 flow for GitHub."""

    @property
    def name(self) -> str:
        return "github"

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = urlencode({
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "read:user user:email",
        })
        return f"https://github.com/login/oauth/authorize?{params}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        # Exchange code for access token
        token_resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=10,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        if "access_token" not in token_data:
            raise ValueError(f"GitHub OAuth failed: {token_data.get('error_description', 'unknown error')}")

        access_token = token_data["access_token"]

        # Fetch user info
        user_resp = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # Fetch primary email if needed
        email = user_data.get("email")
        if not email:
            email_resp = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10,
            )
            email_resp.raise_for_status()
            emails = email_resp.json()
            primary = next((e for e in emails if e.get("primary")), {})
            email = primary.get("email", "")

        return {
            "provider": "github",
            "provider_user_id": str(user_data["id"]),
            "email": email,
            "display_name": user_data.get("name") or user_data.get("login", ""),
            "avatar_url": user_data.get("avatar_url"),
        }
