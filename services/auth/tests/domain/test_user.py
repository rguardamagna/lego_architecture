"""Tests para entidades del dominio."""
import uuid
from datetime import datetime, timezone
from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthProvider, OAuthLink


def make_email(local="test@example.com"):
    return Email(local)


class TestUser:
    def test_create_user_minimal(self):
        uid = uuid.uuid4()
        email = make_email()
        now = datetime.now(timezone.utc)
        user = User(
            id=uid,
            email=email,
            password_hash="hashed_pw",
            display_name="Test User",
            avatar_url=None,
            oauth_links=[],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert user.id == uid
        assert user.email == email
        assert user.display_name == "Test User"
        assert user.is_active is True
        assert user.oauth_links == []

    def test_user_with_oauth(self):
        link = OAuthLink(OAuthProvider.GOOGLE, "google_123")
        user = User(
            id=uuid.uuid4(),
            email=make_email(),
            password_hash=None,
            display_name="OAuth User",
            avatar_url="https://example.com/avatar.png",
            oauth_links=[link],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert user.password_hash is None
        assert len(user.oauth_links) == 1
        assert user.oauth_links[0].provider == OAuthProvider.GOOGLE
        assert user.avatar_url == "https://example.com/avatar.png"

    def test_user_equality_by_id(self):
        uid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        user1 = User(uid, make_email(), "hash", "A", None, [], True, now, now)
        user2 = User(uid, make_email("other@example.com"), "other_hash", "B", None, [], True, now, now)
        assert user1 == user2  # iguales porque mismo ID

    def test_user_hashable(self):
        uid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        u = User(uid, make_email(), "hash", "A", None, [], True, now, now)
        s = {u}
        assert len(s) == 1
