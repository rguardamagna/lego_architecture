"""Error handlers para la app Flask."""
from flask import jsonify


def register_error_handlers(app):
    """Registra manejadores de error con formato estándar."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "bad_request", "message": str(e) or "Bad request"}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found", "message": "Endpoint not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "method_not_allowed", "message": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "internal_error", "message": "Internal server error"}), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"error": "rate_limited", "message": "Too many requests"}), 429
