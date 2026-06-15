"""User entity."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthLink


@dataclass
class User:
    id: uuid.UUID
    email: Email
    password_hash: Optional[str]
    display_name: str
    avatar_url: Optional[str]
    oauth_links: list[OAuthLink]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        email: Email,
        password_hash: Optional[str],
        display_name: str,
        avatar_url: Optional[str] = None,
    ) -> "User":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            avatar_url=avatar_url,
            oauth_links=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
