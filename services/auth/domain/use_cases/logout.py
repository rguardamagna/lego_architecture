"""Logout use case."""
from dataclasses import dataclass
import uuid

from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService


@dataclass
class LogoutRequest:
    refresh_token: str


class LogoutUseCase:
    def __init__(self, repo: UserRepository, token_service: TokenService):
        self._repo = repo
        self._token_service = token_service

    def execute(self, request: LogoutRequest) -> None:
        try:
            payload = self._token_service.verify_refresh_token(request.refresh_token)
        except ValueError as e:
            raise ValueError("Invalid refresh token") from e

        jti = uuid.UUID(payload["jti"])
        self._repo.revoke_refresh_token(jti)
