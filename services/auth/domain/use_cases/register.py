"""Register use case."""
from dataclasses import dataclass
from typing import Optional

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.password import PasswordPolicy, PasswordHash
from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.ports.password_hasher import PasswordHasher


@dataclass
class RegisterRequest:
    email: str
    password: str
    display_name: str


@dataclass
class AuthResult:
    user: User
    access_token: str
    refresh_token: str


class RegisterUserUseCase:
    def __init__(self, repo: UserRepository, hasher: PasswordHasher, token_service: TokenService):
        self._repo = repo
        self._hasher = hasher
        self._token_service = token_service

    def execute(self, request: RegisterRequest) -> AuthResult:
        # Validate password policy
        if not PasswordPolicy.validate(request.password):
            raise ValueError("Password does not meet policy requirements")

        # Validate and normalize email
        email = Email(request.email)

        # Check duplicate
        existing = self._repo.find_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        # Hash password
        hashed = self._hasher.hash(request.password)

        # Create user
        user = User.create(
            email=email,
            password_hash=hashed,
            display_name=request.display_name,
        )

        # Persist
        saved = self._repo.save(user)

        # Generate tokens
        access_token = self._token_service.create_access_token(saved)
        refresh_token, jti = self._token_service.create_refresh_token(saved)

        # Persist refresh token
        self._repo.save_refresh_token(jti, saved.id, None)

        return AuthResult(user=saved, access_token=access_token, refresh_token=refresh_token)
