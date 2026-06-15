"""Tests para el repositorio SQLAlchemy (con SQLite en memoria)."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthProvider, OAuthLink
from adapters.repository.models import Base, UserModel, OAuthLinkModel, RefreshTokenModel
from adapters.repository.user_repository import PostgresUserRepository


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def repo(engine):
    return PostgresUserRepository(engine)


@pytest.fixture
def sample_user():
    return User(
        id=uuid.uuid4(),
        email=Email("test@example.com"),
        password_hash="hashed_password",
        display_name="Test User",
        avatar_url=None,
        oauth_links=[],
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestPostgresUserRepository:
    def test_save_and_find_by_email(self, repo, sample_user):
        saved = repo.save(sample_user)
        assert saved.id == sample_user.id

        found = repo.find_by_email(Email("test@example.com"))
        assert found is not None
        assert found.id == sample_user.id
        assert found.display_name == "Test User"

    def test_save_duplicate_email_raises(self, repo, sample_user):
        repo.save(sample_user)
        dup = User(
            id=uuid.uuid4(),
            email=Email("test@example.com"),
            password_hash="other_hash",
            display_name="Dup",
            avatar_url=None,
            oauth_links=[],
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(ValueError, match="Email already registered"):
            repo.save(dup)

    def test_find_by_email_not_found(self, repo):
        found = repo.find_by_email(Email("nonexistent@example.com"))
        assert found is None

    def test_find_by_id(self, repo, sample_user):
        repo.save(sample_user)
        found = repo.find_by_id(sample_user.id)
        assert found is not None
        assert found.email.value == sample_user.email.value

    def test_find_by_id_not_found(self, repo):
        found = repo.find_by_id(uuid.uuid4())
        assert found is None

    def test_update_user(self, repo, sample_user):
        repo.save(sample_user)
        sample_user.display_name = "Updated Name"
        updated = repo.update(sample_user)
        assert updated.display_name == "Updated Name"

        found = repo.find_by_id(sample_user.id)
        assert found is not None
        assert found.display_name == "Updated Name"

    def test_find_by_oauth_not_found(self, repo):
        found = repo.find_by_oauth("google", "nonexistent")
        assert found is None

    def test_add_and_find_oauth_link(self, repo, sample_user):
        repo.save(sample_user)
        repo.add_oauth_link(sample_user.id, "google", "google_123")

        found = repo.find_by_oauth("google", "google_123")
        assert found is not None
        assert found.id == sample_user.id
        assert len(found.oauth_links) == 1

    def test_refresh_token_lifecycle(self, repo, sample_user):
        repo.save(sample_user)
        jti = uuid.uuid4()
        expires = datetime.now(timezone.utc) + timedelta(days=7)

        repo.save_refresh_token(jti, sample_user.id, expires)
        stored = repo.find_refresh_token(jti)
        assert stored is not None
        assert stored["revoked_at"] is None

        repo.revoke_refresh_token(jti)
        stored = repo.find_refresh_token(jti)
        assert stored is not None
        assert stored["revoked_at"] is not None

    def test_add_oauth_link_multiple_providers(self, repo, sample_user):
        repo.save(sample_user)
        repo.add_oauth_link(sample_user.id, "google", "g123")
        repo.add_oauth_link(sample_user.id, "github", "gh456")

        by_google = repo.find_by_oauth("google", "g123")
        by_github = repo.find_by_oauth("github", "gh456")
        assert by_google is not None
        assert by_github is not None
        assert by_google.id == by_github.id
