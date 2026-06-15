"""OAuth value objects."""
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone


class OAuthProvider(Enum):
    GOOGLE = "google"
    GITHUB = "github"

    @classmethod
    def from_string(cls, value: str) -> "OAuthProvider":
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"Unknown OAuth provider: {value}")


@dataclass(frozen=True)
class OAuthLink:
    """Links a user to an external OAuth provider."""

    provider: OAuthProvider
    provider_user_id: str
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc))
