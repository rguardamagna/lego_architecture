"""Flask routes: Auth API."""
import uuid
import json
from functools import wraps

from flask import Blueprint, request, jsonify, current_app

from domain.use_cases.register import RegisterUserUseCase, RegisterRequest
from domain.use_cases.login import AuthenticateUserUseCase, LoginRequest
from domain.use_cases.refresh import RefreshTokenUseCase, RefreshRequest
from domain.use_cases.logout import LogoutUseCase, LogoutRequest
from domain.use_cases.get_current_user import GetCurrentUserUseCase
from domain.use_cases.oauth_auth import OAuthAuthenticateUseCase, OAuthRequest

auth_bp = Blueprint("auth", __name__)

# Inyectados por create_app
auth_bp.repo = None
auth_bp.hasher = None
auth_bp.token_service = None
auth_bp.oauth_providers = {}


def _get_repo():
    return auth_bp.repo


def _get_hasher():
    return auth_bp.hasher


def _get_token_service():
    return auth_bp.token_service


def _get_oauth_providers():
    return auth_bp.oauth_providers or {}


# ── Middleware ─────────────────────────────────────────────────


def jwt_required(f):
    """Decorator: extrae y verifica el access token, inyecta user_id."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "unauthorized", "message": "Missing or invalid token"}), 401

        token = auth_header[7:]
        try:
            payload = _get_token_service().verify_access_token(token)
        except ValueError as e:
            return jsonify({"error": "unauthorized", "message": str(e)}), 401

        kwargs["user_id"] = uuid.UUID(payload["sub"])
        return f(*args, **kwargs)

    return decorated


# ── Endpoints ─────────────────────────────────────────────────


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "").strip()

    if not email or not password or not display_name:
        return jsonify({"error": "validation_error", "message": "email, password and display_name are required"}), 400

    uc = RegisterUserUseCase(repo=_get_repo(), hasher=_get_hasher(), token_service=_get_token_service())
    try:
        result = uc.execute(RegisterRequest(email=email, password=password, display_name=display_name))
    except ValueError as e:
        msg = str(e)
        if "password" in msg.lower():
            return jsonify({"error": "weak_password", "message": msg}), 400
        if "email already registered" in msg.lower():
            return jsonify({"error": "duplicate_email", "message": msg}), 409
        if "email" in msg.lower():
            return jsonify({"error": "invalid_email", "message": msg}), 400
        return jsonify({"error": "registration_failed", "message": msg}), 400
    except Exception as e:
        return jsonify({"error": "internal_error", "message": "Registration failed"}), 500

    return jsonify({
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user": {
            "id": str(result.user.id),
            "email": result.user.email.value,
            "display_name": result.user.display_name,
        },
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "validation_error", "message": "email and password are required"}), 400

    uc = AuthenticateUserUseCase(repo=_get_repo(), hasher=_get_hasher(), token_service=_get_token_service())
    try:
        result = uc.execute(LoginRequest(email=email, password=password))
    except ValueError:
        return jsonify({"error": "invalid_credentials", "message": "Invalid email or password"}), 401
    except Exception:
        return jsonify({"error": "internal_error", "message": "Login failed"}), 500

    return jsonify({
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user": {
            "id": str(result.user.id),
            "email": result.user.email.value,
            "display_name": result.user.display_name,
        },
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token", "")

    if not refresh_token:
        return jsonify({"error": "validation_error", "message": "refresh_token is required"}), 400

    uc = RefreshTokenUseCase(repo=_get_repo(), token_service=_get_token_service())
    try:
        result = uc.execute(RefreshRequest(refresh_token=refresh_token))
    except ValueError:
        return jsonify({"error": "invalid_token", "message": "Invalid or expired refresh token"}), 401
    except Exception:
        return jsonify({"error": "internal_error", "message": "Refresh failed"}), 500

    return jsonify({
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token", "")

    if not refresh_token:
        return jsonify({"error": "validation_error", "message": "refresh_token is required"}), 400

    uc = LogoutUseCase(repo=_get_repo(), token_service=_get_token_service())
    try:
        uc.execute(LogoutRequest(refresh_token=refresh_token))
    except ValueError:
        return jsonify({"error": "invalid_token", "message": "Invalid or expired refresh token"}), 401
    except Exception:
        return jsonify({"error": "internal_error", "message": "Logout failed"}), 500

    return "", 204


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me(user_id: uuid.UUID):
    uc = GetCurrentUserUseCase(repo=_get_repo())
    user = uc.execute(user_id)
    if not user:
        return jsonify({"error": "not_found", "message": "User not found"}), 404

    return jsonify({
        "id": str(user.id),
        "email": user.email.value,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "oauth_providers": [link.provider.value for link in user.oauth_links],
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }), 200


# ── OAuth ──────────────────────────────────────────────────────


@auth_bp.route("/oauth/<provider>/login", methods=["GET"])
def oauth_login(provider: str):
    from uuid import uuid4

    providers = _get_oauth_providers()
    p = providers.get(provider)
    if not p:
        return jsonify({"error": "invalid_provider", "message": f"Unsupported OAuth provider: {provider}"}), 400

    state = str(uuid4())
    redirect_uri = request.args.get("redirect_uri", "")
    if not redirect_uri:
        redirect_uri = request.host_url.rstrip("/") + f"/auth/oauth/{provider}/callback"

    url = p.get_authorization_url(state=state, redirect_uri=redirect_uri)
    return jsonify({"authorization_url": url, "state": state, "redirect_uri": redirect_uri}), 200


@auth_bp.route("/oauth/<provider>/callback", methods=["GET"])
def oauth_callback(provider: str):
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    stored_state = request.args.get("stored_state", "") or request.args.get("state", "")
    redirect_uri = request.args.get("redirect_uri", "")
    if not redirect_uri:
        redirect_uri = request.host_url.rstrip("/") + f"/auth/oauth/{provider}/callback"

    if not code:
        return jsonify({"error": "missing_code", "message": "Authorization code is required"}), 400

    providers = _get_oauth_providers()
    p = providers.get(provider)
    if not p:
        return jsonify({"error": "invalid_provider", "message": f"Unsupported OAuth provider: {provider}"}), 400

    uc = OAuthAuthenticateUseCase(
        repo=_get_repo(),
        providers=providers,
        token_service=_get_token_service(),
    )
    try:
        result = uc.execute(OAuthRequest(
            provider=provider,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
            stored_state=stored_state,
        ))
    except ValueError as e:
        return jsonify({"error": "oauth_failed", "message": str(e)}), 401
    except Exception as e:
        return jsonify({"error": "oauth_failed", "message": "OAuth authentication failed"}), 500

    return jsonify({
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user": {
            "id": str(result.user.id),
            "email": result.user.email.value,
            "display_name": result.user.display_name,
        },
    }), 200
