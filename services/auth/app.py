"""Auth Service entry point."""
import os

from sqlalchemy import create_engine

from adapters.repository.models import Base
from adapters.repository.user_repository import PostgresUserRepository
from adapters.password.bcrypt_hasher import BCryptPasswordHasher
from adapters.token.jwt_service import JWTService
from adapters.oauth.github import GitHubOAuthProvider
from adapters.oauth.google import GoogleOAuthProvider
from adapters.flask.app import create_app


def main():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./auth.db")
    jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production")
    cors_origins = os.getenv("CORS_ORIGINS", "*")

    # Database
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # Dependencies
    repo = PostgresUserRepository(engine)
    hasher = BCryptPasswordHasher()
    token_service = JWTService(
        secret=jwt_secret,
        access_expire_minutes=int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "15")),
        refresh_expire_days=int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", "7")),
    )

    # OAuth providers (configurable via env)
    oauth_providers = {}
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if google_client_id and google_client_secret:
        oauth_providers["google"] = GoogleOAuthProvider(google_client_id, google_client_secret)

    github_client_id = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    if github_client_id and github_client_secret:
        oauth_providers["github"] = GitHubOAuthProvider(github_client_id, github_client_secret)

    # App
    app = create_app(
        repo=repo,
        hasher=hasher,
        token_service=token_service,
        jwt_secret=jwt_secret,
        cors_origins=cors_origins,
        oauth_providers=oauth_providers,
    )

    return app


if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
