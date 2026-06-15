"""Postgres/SQLAlchemy user repository adapter."""
from datetime import datetime, timezone
from typing import Optional, Any
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from domain.entities.user import User
from domain.value_objects.email import Email
from domain.value_objects.oauth import OAuthProvider, OAuthLink
from domain.ports.user_repository import UserRepository
from adapters.repository.models import Base, UserModel, OAuthLinkModel, RefreshTokenModel


class PostgresUserRepository(UserRepository):
    """SQLAlchemy-based repository. Works with PostgreSQL or SQLite."""

    def __init__(self, engine):
        self._session_factory = scoped_session(sessionmaker(bind=engine))

    def _to_domain(self, model: UserModel) -> User:
        oauth_links = [
            OAuthLink(
                provider=OAuthProvider.from_string(link.provider),
                provider_user_id=link.provider_user_id,
                created_at=link.created_at,
            )
            for link in model.oauth_links
        ]
        return User(
            id=model.id,
            email=Email(model.email),
            password_hash=model.password_hash,
            display_name=model.display_name,
            avatar_url=model.avatar_url,
            oauth_links=oauth_links,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, user: User) -> User:
        session = self._session_factory()
        try:
            existing = session.query(UserModel).filter(UserModel.email == user.email.value).first()
            if existing:
                raise ValueError("Email already registered")

            model = UserModel(
                id=user.id,
                email=user.email.value,
                password_hash=user.password_hash,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            session.add(model)
            session.commit()
            return user
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise ValueError("Database error") from e
        finally:
            session.close()

    def update(self, user: User) -> User:
        session = self._session_factory()
        try:
            model = session.query(UserModel).filter(UserModel.id == user.id).first()
            if not model:
                raise ValueError("User not found")

            model.email = user.email.value
            model.password_hash = user.password_hash
            model.display_name = user.display_name
            model.avatar_url = user.avatar_url
            model.is_active = user.is_active
            model.updated_at = datetime.now(timezone.utc)
            session.commit()
            return user
        except ValueError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise ValueError("Database error") from e
        finally:
            session.close()

    def find_by_email(self, email: Email) -> Optional[User]:
        session = self._session_factory()
        try:
            model = session.query(UserModel).filter(UserModel.email == email.value).first()
            return self._to_domain(model) if model else None
        finally:
            session.close()

    def find_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        session = self._session_factory()
        try:
            model = session.query(UserModel).filter(UserModel.id == user_id).first()
            return self._to_domain(model) if model else None
        finally:
            session.close()

    def find_by_oauth(self, provider: str, provider_user_id: str) -> Optional[User]:
        session = self._session_factory()
        try:
            link = (
                session.query(OAuthLinkModel)
                .filter(
                    OAuthLinkModel.provider == provider,
                    OAuthLinkModel.provider_user_id == provider_user_id,
                )
                .first()
            )
            if not link:
                return None
            model = session.query(UserModel).filter(UserModel.id == link.user_id).first()
            return self._to_domain(model) if model else None
        finally:
            session.close()

    def save_refresh_token(self, jti: uuid.UUID, user_id: uuid.UUID, expires_at) -> None:
        session = self._session_factory()
        try:
            if expires_at is None:
                from datetime import timedelta
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            model = RefreshTokenModel(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at,
            )
            session.add(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def find_refresh_token(self, jti: uuid.UUID) -> Optional[dict[str, Any]]:
        session = self._session_factory()
        try:
            model = session.query(RefreshTokenModel).filter(RefreshTokenModel.jti == jti).first()
            if not model:
                return None
            return {
                "jti": model.jti,
                "user_id": model.user_id,
                "expires_at": model.expires_at,
                "revoked_at": model.revoked_at,
            }
        finally:
            session.close()

    def revoke_refresh_token(self, jti: uuid.UUID) -> None:
        session = self._session_factory()
        try:
            model = session.query(RefreshTokenModel).filter(RefreshTokenModel.jti == jti).first()
            if model:
                model.revoked_at = datetime.now(timezone.utc)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_oauth_link(self, user_id: uuid.UUID, provider: str, provider_user_id: str) -> None:
        session = self._session_factory()
        try:
            model = OAuthLinkModel(
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
            )
            session.add(model)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
