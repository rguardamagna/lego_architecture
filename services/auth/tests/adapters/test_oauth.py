"""Tests para adapters OAuth mockeando HTTP."""
import uuid
import json

import pytest
import responses

from adapters.oauth.github import GitHubOAuthProvider
from adapters.oauth.google import GoogleOAuthProvider


# ── GitHub ──────────────────────────────────────────────────


class TestGitHubOAuth:
    @pytest.fixture
    def provider(self):
        return GitHubOAuthProvider(
            client_id="test-github-client",
            client_secret="test-github-secret",
        )

    def test_name(self, provider):
        assert provider.name == "github"

    def test_get_authorization_url(self, provider):
        url = provider.get_authorization_url(state="abc123", redirect_uri="http://localhost:5173/callback")
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=test-github-client" in url
        assert "state=abc123" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A5173%2Fcallback" in url
        assert "scope=read%3Auser+user%3Aemail" in url

    @responses.activate
    def test_exchange_code_success(self, provider):
        # Mock token exchange
        responses.post(
            "https://github.com/login/oauth/access_token",
            json={"access_token": "gho_test_token123", "token_type": "bearer"},
            status=200,
        )

        # Mock user info
        responses.get(
            "https://api.github.com/user",
            json={
                "id": 12345,
                "email": "octocat@github.com",
                "name": "Octocat",
                "login": "octocat",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            },
            status=200,
        )

        result = provider.exchange_code(code="test_code", redirect_uri="http://localhost:5173/callback")

        assert result["provider"] == "github"
        assert result["provider_user_id"] == "12345"
        assert result["email"] == "octocat@github.com"
        assert result["display_name"] == "Octocat"
        assert result["avatar_url"] == "https://avatars.githubusercontent.com/u/12345"

    @responses.activate
    def test_exchange_code_uses_emails_fallback(self, provider):
        """Si el email del user endpoint es null, busca en /user/emails."""
        responses.post(
            "https://github.com/login/oauth/access_token",
            json={"access_token": "gho_test_token123", "token_type": "bearer"},
        )

        # User endpoint without email
        responses.get(
            "https://api.github.com/user",
            json={
                "id": 67890,
                "email": None,
                "name": "No Email User",
                "login": "noemail",
                "avatar_url": None,
            },
        )

        # Emails endpoint
        responses.get(
            "https://api.github.com/user/emails",
            json=[
                {"email": "primary@example.com", "primary": True, "verified": True},
                {"email": "secondary@example.com", "primary": False},
            ],
        )

        result = provider.exchange_code(code="test_code", redirect_uri="http://localhost:5173/callback")
        assert result["email"] == "primary@example.com"

    @responses.activate
    def test_exchange_code_failure(self, provider):
        responses.post(
            "https://github.com/login/oauth/access_token",
            json={"error": "bad_verification_code", "error_description": "The code passed is incorrect or expired."},
            status=200,
        )

        with pytest.raises(ValueError, match="GitHub OAuth failed"):
            provider.exchange_code(code="bad_code", redirect_uri="http://localhost:5173/callback")


# ── Google ──────────────────────────────────────────────────


class TestGoogleOAuth:
    @pytest.fixture
    def provider(self):
        return GoogleOAuthProvider(
            client_id="test-google-client",
            client_secret="test-google-secret",
        )

    def test_name(self, provider):
        assert provider.name == "google"

    def test_get_authorization_url(self, provider):
        url = provider.get_authorization_url(state="xyz789", redirect_uri="http://localhost:5173/callback")
        assert "accounts.google.com" in url
        assert "client_id=test-google-client" in url
        assert "state=xyz789" in url
        assert "response_type=code" in url

    @responses.activate
    def test_exchange_code_success(self, provider):
        # Mock token endpoint
        import jwt as pyjwt
        import time

        fake_id_token = pyjwt.encode(
            {
                "sub": "1234567890",
                "email": "user@gmail.com",
                "name": "Google User",
                "picture": "https://lh3.googleusercontent.com/a/photo",
                "iat": int(time.time()),
                "exp": int(time.time()) + 3600,
            },
            key="fake-secret",
            algorithm="HS256",
        )

        responses.post(
            "https://oauth2.googleapis.com/token",
            json={
                "access_token": "ya29.test_token",
                "id_token": fake_id_token,
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )

        result = provider.exchange_code(code="test_code", redirect_uri="http://localhost:5173/callback")

        assert result["provider"] == "google"
        assert result["provider_user_id"] == "1234567890"
        assert result["email"] == "user@gmail.com"
        assert result["display_name"] == "Google User"
        assert result["avatar_url"] == "https://lh3.googleusercontent.com/a/photo"

    @responses.activate
    def test_exchange_code_missing_id_token(self, provider):
        responses.post(
            "https://oauth2.googleapis.com/token",
            json={
                "access_token": "ya29.test_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )

        with pytest.raises(ValueError, match="no id_token"):
            provider.exchange_code(code="test_code", redirect_uri="http://localhost:5173/callback")
