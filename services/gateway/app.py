"""Gateway application factory."""
from flask import Flask, jsonify, request

from gateway.config import Settings
from gateway.middleware.cors import CORSMiddleware
from gateway.middleware.jwt import JWTPreVerifyMiddleware
from gateway.middleware.logging import LoggingMiddleware
from gateway.router.routes import init_routes, find_route
from gateway.router.proxy import proxy_request


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Gateway Flask application.

    Args:
        settings: Optional Settings instance. If omitted, loads from env.

    Returns:
        Configured Flask app with middleware stack.
    """
    if settings is None:
        settings = Settings()

    app = Flask(__name__)

    init_routes(settings.route_map)

    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "service": "gateway",
            "version": "0.1.0",
        })

    @app.route("/api/v1/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def proxy(subpath):
        path = "/" + request.path.lstrip("/")
        route = find_route(path)

        if route is None:
            return jsonify({"error": "not_found", "message": "No route matches"}), 404

        target, remaining = route
        upstream_url = f"{target}{remaining}"
        if request.query_string:
            upstream_url += f"?{request.query_string.decode()}"

        status, headers, body = proxy_request(
            method=request.method,
            url=upstream_url,
            headers={k: v for k, v in request.headers if k.lower() not in ("host", "content-length")},
            body=request.data,
            timeout=settings.upstream_timeout,
        )
        return body, status, {k: v for k, v in headers.items() if k.lower() not in ("transfer-encoding",)}

    # Apply WSGI middleware (innermost first = last applied)
    app.wsgi_app = LoggingMiddleware(app.wsgi_app)
    app.wsgi_app = CORSMiddleware(app.wsgi_app, origins=settings.cors_origins)
    app.wsgi_app = JWTPreVerifyMiddleware(
        app.wsgi_app,
        secret=settings.jwt_secret,
        jwt_preverify=settings.jwt_preverify,
    )

    return app
