"""Flask application factory."""
from typing import Optional
import uuid

from flask import Flask

from domain.ports.user_repository import UserRepository
from domain.ports.token_service import TokenService
from domain.ports.password_hasher import PasswordHasher
from domain.ports.oauth_service import OAuthProvider

# Lazy imports to avoid circular deps at module level
from .routes import auth_bp
from .error_handlers import register_error_handlers


def create_app(
    repo: UserRepository,
    hasher: PasswordHasher,
    token_service: TokenService,
    jwt_secret: str,
    cors_origins: str = "*",
    oauth_providers: Optional[dict[str, OAuthProvider]] = None,
) -> Flask:
    app = Flask(__name__)
    app.config["jwt_secret"] = jwt_secret
    app.config["cors_origins"] = cors_origins
    app.config["oauth_providers"] = oauth_providers or {}

    # Registrar blueprint con dependencias
    auth_bp.repo = repo
    auth_bp.hasher = hasher
    auth_bp.token_service = token_service
    auth_bp.oauth_providers = oauth_providers or {}

    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Health check directo
    @app.route("/health")
    def health():
        from lego_shared import build_health_response
        return build_health_response(service="auth", version="0.1.0")

    # CORS simple
    @app.after_request
    def add_cors(response):
        response.headers["Access-Control-Allow-Origin"] = cors_origins
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    register_error_handlers(app)

    return app
