"""Get current user use case."""
import uuid
from typing import Optional

from domain.entities.user import User
from domain.ports.user_repository import UserRepository


class GetCurrentUserUseCase:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def execute(self, user_id: uuid.UUID) -> Optional[User]:
        return self._repo.find_by_id(user_id)
