"""Login use case."""
from dataclasses import dataclass

from domain.value_objects.email import Email
from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.ports.password_hasher import PasswordHasher
from domain.use_cases.register import AuthResult


@dataclass
class LoginRequest:
    email: str
    password: str


class AuthenticateUserUseCase:
    def __init__(self, repo: UserRepository, hasher: PasswordHasher, token_service: TokenService):
        self._repo = repo
        self._hasher = hasher
        self._token_service = token_service

    def execute(self, request: LoginRequest) -> AuthResult:
        email = Email(request.email)

        user = self._repo.find_by_email(email)
        if not user:
            raise ValueError("Invalid credentials")

        if not user.password_hash:
            raise ValueError("Invalid credentials")

        if not self._hasher.verify(request.password, user.password_hash):
            raise ValueError("Invalid credentials")

        access_token = self._token_service.create_access_token(user)
        refresh_token, jti = self._token_service.create_refresh_token(user)

        # Persist refresh token
        self._repo.save_refresh_token(jti, user.id, None)

        return AuthResult(user=user, access_token=access_token, refresh_token=refresh_token)
