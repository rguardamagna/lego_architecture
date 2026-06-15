"""Refresh token use case."""
from dataclasses import dataclass
import uuid

from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.use_cases.register import AuthResult


@dataclass
class RefreshRequest:
    refresh_token: str


class RefreshTokenUseCase:
    def __init__(self, repo: UserRepository, token_service: TokenService):
        self._repo = repo
        self._token_service = token_service

    def execute(self, request: RefreshRequest) -> AuthResult:
        # Verify the refresh token
        try:
            payload = self._token_service.verify_refresh_token(request.refresh_token)
        except ValueError as e:
            raise ValueError("Invalid refresh token") from e

        jti = uuid.UUID(payload["jti"])
        user_id = uuid.UUID(payload["sub"])

        # Check if token has been revoked
        stored = self._repo.find_refresh_token(jti)
        if stored and stored.get("revoked_at"):
            raise ValueError("Invalid refresh token")
        user = self._repo.find_by_id(user_id)
        if not user:
            raise ValueError("Invalid refresh token")

        # Generate new tokens (rotation)
        new_access = self._token_service.create_access_token(user)
        new_refresh, new_jti = self._token_service.create_refresh_token(user)

        # Persist new refresh token (replace old)
        self._repo.save_refresh_token(new_jti, user.id, None)

        return AuthResult(user=user, access_token=new_access, refresh_token=new_refresh)
