"""Tests para use cases del dominio con repositorio in-memory."""
import uuid
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

import pytest

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.password import PasswordPolicy
from domain.value_objects.oauth import OAuthProvider, OAuthLink
from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.ports.password_hasher import PasswordHasher
from domain.ports.oauth_service import OAuthProvider as OAuthProviderPort
from domain.use_cases.register import RegisterUserUseCase, RegisterRequest
from domain.use_cases.login import AuthenticateUserUseCase, LoginRequest
from domain.use_cases.refresh import RefreshTokenUseCase, RefreshRequest
from domain.use_cases.logout import LogoutUseCase, LogoutRequest
from domain.use_cases.get_current_user import GetCurrentUserUseCase
from domain.use_cases.oauth_auth import OAuthAuthenticateUseCase, OAuthRequest


# ── In-memory implementations for tests ──────────────────────────


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self._users: dict[uuid.UUID, User] = {}
        self._emails: dict[str, User] = {}
        self._oauth: dict[tuple[str, str], User] = {}
        self._refresh_tokens: dict[uuid.UUID, dict] = {}

    def save(self, user: User) -> User:
        if user.email.value in self._emails:
            raise ValueError("Email already registered")
        self._users[user.id] = user
        self._emails[user.email.value] = user
        return user

    def update(self, user: User) -> User:
        self._users[user.id] = user
        self._emails[user.email.value] = user
        return user

    def find_by_email(self, email: Email) -> Optional[User]:
        return self._emails.get(email.value)

    def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self._users.get(user_id)

    def find_by_oauth(self, provider: str, provider_user_id: str) -> Optional[User]:
        return self._oauth.get((provider, provider_user_id))

    def save_refresh_token(self, jti: uuid.UUID, user_id: uuid.UUID, expires_at) -> None:
        self._refresh_tokens[jti] = {"user_id": user_id, "expires_at": expires_at, "revoked_at": None}

    def find_refresh_token(self, jti: uuid.UUID) -> Optional[dict]:
        return self._refresh_tokens.get(jti)

    def revoke_refresh_token(self, jti: uuid.UUID) -> None:
        if jti in self._refresh_tokens:
            self._refresh_tokens[jti]["revoked_at"] = datetime.now(timezone.utc)

    def add_oauth_link(self, user_id: uuid.UUID, provider: str, provider_user_id: str) -> None:
        user = self._users.get(user_id)
        if user:
            link = OAuthLink(OAuthProvider.from_string(provider), provider_user_id)
            user.oauth_links.append(link)
            self._oauth[(provider, provider_user_id)] = user


class FakePasswordHasher(PasswordHasher):
    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


class FakeTokenService(TokenService):
    def __init__(self):
        self._access_tokens: dict[str, dict] = {}
        self._refresh_tokens: dict[str, dict] = {}
        self._revoked_jtis: set[uuid.UUID] = set()

    def create_access_token(self, user: User) -> str:
        token = f"access:{user.id}:{uuid.uuid4()}"
        self._access_tokens[token] = {"sub": str(user.id), "email": user.email.value}
        return token

    def create_refresh_token(self, user: User) -> tuple[str, uuid.UUID]:
        jti = uuid.uuid4()
        token = f"refresh:{user.id}:{jti}"
        self._refresh_tokens[token] = {"sub": str(user.id), "jti": str(jti)}
        return token, jti

    def verify_access_token(self, token: str) -> dict:
        if token not in self._access_tokens:
            raise ValueError("Invalid access token")
        return self._access_tokens[token]

    def verify_refresh_token(self, token: str) -> dict:
        if token not in self._refresh_tokens:
            raise ValueError("Invalid refresh token")
        return self._refresh_tokens[token]


class FakeOAuthProvider(OAuthProviderPort):
    def __init__(self, provider_name: str, user_info: dict):
        self._name = provider_name
        self._user_info = user_info

    @property
    def name(self) -> str:
        return self._name

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://{self._name}.com/auth?state={state}"

    def exchange_code(self, code: str, redirect_uri: str) -> dict:
        return self._user_info


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def repo():
    return InMemoryUserRepository()


@pytest.fixture
def hasher():
    return FakePasswordHasher()


@pytest.fixture
def token_svc():
    return FakeTokenService()


@pytest.fixture
def google_provider():
    return FakeOAuthProvider("google", {
        "email": "user@gmail.com",
        "provider_user_id": "google_123",
        "display_name": "Google User",
        "avatar_url": "https://google.com/avatar.png",
    })


# ── Tests: RegisterUserUseCase ───────────────────────────────────


class TestRegister:
    def test_register_success(self, repo, hasher, token_svc):
        uc = RegisterUserUseCase(repo, hasher, token_svc)
        result = uc.execute(RegisterRequest(email="new@user.com", password="Str0ng!Pass", display_name="New User"))

        assert result.user is not None
        assert result.user.email.value == "new@user.com"
        assert result.user.display_name == "New User"
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user.password_hash != "Str0ng!Pass"

    def test_register_duplicate_email(self, repo, hasher, token_svc):
        uc = RegisterUserUseCase(repo, hasher, token_svc)
        uc.execute(RegisterRequest(email="dup@user.com", password="Str0ng!Pass", display_name="First"))
        with pytest.raises(ValueError, match="already registered"):
            uc.execute(RegisterRequest(email="dup@user.com", password="Str0ng!Pass", display_name="Second"))

    def test_register_weak_password(self, repo, hasher, token_svc):
        uc = RegisterUserUseCase(repo, hasher, token_svc)
        with pytest.raises(ValueError, match="Password does not meet policy"):
            uc.execute(RegisterRequest(email="weak@user.com", password="short", display_name="Weak"))

    def test_register_invalid_email(self, repo, hasher, token_svc):
        uc = RegisterUserUseCase(repo, hasher, token_svc)
        with pytest.raises(ValueError, match="Invalid email"):
            uc.execute(RegisterRequest(email="notanemail", password="Str0ng!Pass", display_name="Bad"))


# ── Tests: AuthenticateUserUseCase ───────────────────────────────


class TestLogin:
    def test_login_success(self, repo, hasher, token_svc):
        # Register first
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_uc.execute(RegisterRequest(email="login@test.com", password="Str0ng!Pass", display_name="Login Test"))

        # Login
        uc = AuthenticateUserUseCase(repo, hasher, token_svc)
        result = uc.execute(LoginRequest(email="login@test.com", password="Str0ng!Pass"))

        assert result.user is not None
        assert result.access_token is not None
        assert result.refresh_token is not None

    def test_login_wrong_password(self, repo, hasher, token_svc):
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_uc.execute(RegisterRequest(email="wrong@test.com", password="Str0ng!Pass", display_name="Wrong"))

        uc = AuthenticateUserUseCase(repo, hasher, token_svc)
        with pytest.raises(ValueError, match="Invalid credentials"):
            uc.execute(LoginRequest(email="wrong@test.com", password="WrongPass1!"))

    def test_login_user_not_found(self, repo, hasher, token_svc):
        uc = AuthenticateUserUseCase(repo, hasher, token_svc)
        with pytest.raises(ValueError, match="Invalid credentials"):
            uc.execute(LoginRequest(email="nonexistent@test.com", password="Str0ng!Pass"))


# ── Tests: RefreshTokenUseCase ────────────────────────────────────


class TestRefresh:
    def test_refresh_success(self, repo, hasher, token_svc):
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_result = reg_uc.execute(RegisterRequest(email="refresh@test.com", password="Str0ng!Pass", display_name="Refresh"))

        uc = RefreshTokenUseCase(repo, token_svc)
        result = uc.execute(RefreshRequest(refresh_token=reg_result.refresh_token))

        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.refresh_token != reg_result.refresh_token  # rotation

    def test_refresh_invalid_token(self, repo, hasher, token_svc):
        uc = RefreshTokenUseCase(repo, token_svc)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            uc.execute(RefreshRequest(refresh_token="fake-token"))


# ── Tests: LogoutUseCase ─────────────────────────────────────────


class TestLogout:
    def test_logout_revokes_token(self, repo, hasher, token_svc):
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_result = reg_uc.execute(RegisterRequest(email="logout@test.com", password="Str0ng!Pass", display_name="Logout"))

        uc = LogoutUseCase(repo, token_svc)
        uc.execute(LogoutRequest(refresh_token=reg_result.refresh_token))

        # Verify refresh token no longer works
        refresh_uc = RefreshTokenUseCase(repo, token_svc)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            refresh_uc.execute(RefreshRequest(refresh_token=reg_result.refresh_token))


# ── Tests: GetCurrentUserUseCase ─────────────────────────────────


class TestGetCurrentUser:
    def test_get_user_success(self, repo, hasher, token_svc):
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_result = reg_uc.execute(RegisterRequest(email="me@test.com", password="Str0ng!Pass", display_name="Me"))

        uc = GetCurrentUserUseCase(repo)
        user = uc.execute(reg_result.user.id)
        assert user is not None
        assert user.email.value == "me@test.com"
        assert user.display_name == "Me"

    def test_get_user_not_found(self, repo, hasher, token_svc):
        uc = GetCurrentUserUseCase(repo)
        user = uc.execute(uuid.uuid4())
        assert user is None


# ── Tests: OAuthAuthenticateUseCase ──────────────────────────────


class TestOAuth:
    def test_oauth_new_user(self, repo, hasher, token_svc, google_provider, caplog):
        import logging
        caplog.set_level(logging.INFO)
        uc = OAuthAuthenticateUseCase(
            repo=repo,
            providers={"google": google_provider},
            token_service=token_svc,
            hasher=hasher,
        )
        result = uc.execute(OAuthRequest(
            provider="google",
            code="auth_code_123",
            state="state_abc",
            redirect_uri="http://localhost:8000/api/v1/auth/oauth/google/callback",
            stored_state="state_abc",
        ))
        assert result.user is not None
        assert result.user.email.value == "user@gmail.com"
        assert result.access_token is not None
        assert result.refresh_token is not None
        # Should have OAuth link
        assert len(result.user.oauth_links) == 1

    def test_oauth_existing_user_by_email(self, repo, hasher, token_svc, google_provider):
        # Register user with same email first
        reg_uc = RegisterUserUseCase(repo, hasher, token_svc)
        reg_uc.execute(RegisterRequest(email="user@gmail.com", password="Str0ng!Pass", display_name="Existing"))

        uc = OAuthAuthenticateUseCase(
            repo=repo,
            providers={"google": google_provider},
            token_service=token_svc,
            hasher=hasher,
        )
        result = uc.execute(OAuthRequest(
            provider="google",
            code="code_456",
            state="state_def",
            redirect_uri="http://localhost:8000/api/v1/auth/oauth/google/callback",
            stored_state="state_def",
        ))
        assert result.user is not None
        assert result.user.email.value == "user@gmail.com"

    def test_oauth_state_mismatch(self, repo, hasher, token_svc, google_provider):
        uc = OAuthAuthenticateUseCase(
            repo=repo,
            providers={"google": google_provider},
            token_service=token_svc,
            hasher=hasher,
        )
        with pytest.raises(ValueError, match="state mismatch"):
            uc.execute(OAuthRequest(
                provider="google",
                code="code",
                state="wrong_state",
                redirect_uri="http://localhost:8000/api/v1/auth/oauth/google/callback",
                stored_state="expected_state",
            ))

    def test_oauth_invalid_provider(self, repo, hasher, token_svc, google_provider):
        uc = OAuthAuthenticateUseCase(
            repo=repo,
            providers={"google": google_provider},
            token_service=token_svc,
            hasher=hasher,
        )
        with pytest.raises(ValueError, match="Unsupported provider"):
            uc.execute(OAuthRequest(
                provider="twitter",
                code="code",
                state="state",
                redirect_uri="http://localhost:8000/api/v1/auth/oauth/twitter/callback",
                stored_state="state",
            ))
