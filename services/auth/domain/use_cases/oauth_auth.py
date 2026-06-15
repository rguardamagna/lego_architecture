"""OAuth authentication use case."""
from dataclasses import dataclass
from typing import Optional

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthProvider, OAuthLink
from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.ports.password_hasher import PasswordHasher
from domain.ports.oauth_service import OAuthProvider as OAuthProviderPort
from domain.use_cases.register import AuthResult


@dataclass
class OAuthRequest:
    provider: str
    code: str
    state: str
    redirect_uri: str
    stored_state: str


class OAuthAuthenticateUseCase:
    def __init__(
        self,
        repo: UserRepository,
        providers: dict[str, OAuthProviderPort],
        token_service: TokenService,
        hasher: Optional[PasswordHasher] = None,
    ):
        self._repo = repo
        self._providers = providers
        self._token_service = token_service
        self._hasher = hasher

    def execute(self, request: OAuthRequest) -> AuthResult:
        # Validate state (CSRF protection)
        if request.state != request.stored_state:
            raise ValueError("OAuth state mismatch")

        # Get provider implementation
        provider = self._providers.get(request.provider)
        if not provider:
            raise ValueError(f"Unsupported provider: {request.provider}")

        # Exchange code for user info
        user_info = provider.exchange_code(request.code, request.redirect_uri)

        # Try to find existing user by OAuth link
        user = self._repo.find_by_oauth(request.provider, user_info["provider_user_id"])

        # If not found, try by email
        if not user:
            email = Email(user_info["email"])
            user = self._repo.find_by_email(email)

        # If still not found, create new user
        if not user:
            user = User.create(
                email=Email(user_info["email"]),
                password_hash=None,
                display_name=user_info.get("display_name", user_info["email"]),
                avatar_url=user_info.get("avatar_url"),
            )
            user = self._repo.save(user)

        # Add OAuth link if not present
        has_link = any(
            link.provider.value == request.provider and link.provider_user_id == user_info["provider_user_id"]
            for link in user.oauth_links
        )
        if not has_link:
            self._repo.add_oauth_link(user.id, request.provider, user_info["provider_user_id"])

        # Generate tokens
        access_token = self._token_service.create_access_token(user)
        refresh_token, jti = self._token_service.create_refresh_token(user)

        # Persist refresh token
        self._repo.save_refresh_token(jti, user.id, None)

        # Refresh user from repo to get updated oauth_links
        user = self._repo.find_by_id(user.id)
        assert user is not None

        return AuthResult(user=user, access_token=access_token, refresh_token=refresh_token)
