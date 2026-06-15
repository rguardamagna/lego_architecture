"""WSGI middleware: optional JWT pre-verification."""
import json

from lego_shared.jwt_utils import verify_access_token


class JWTPreVerifyMiddleware:
    """Optionally verifies JWT tokens before passing to upstream.

    This is a defense-in-depth layer. Each service still verifies its
    own JWT independently. This middleware rejects obviously invalid
    tokens early, saving upstream round-trips.

    If no Authorization header is present, the request passes through.
    """

    def __init__(self, app, secret: str, jwt_preverify: bool = True):
        self.app = app
        self.secret = secret
        self.jwt_preverify = jwt_preverify

    def __call__(self, environ, start_response):
        if not self.jwt_preverify:
            return self.app(environ, start_response)

        auth = environ.get("HTTP_AUTHORIZATION", "")
        if not auth:
            return self.app(environ, start_response)

        if not auth.startswith("Bearer "):
            return self._unauthorized(start_response, "Invalid authorization scheme")

        token = auth[len("Bearer "):]
        try:
            payload = verify_access_token(token, self.secret)
        except ValueError as e:
            return self._unauthorized(start_response, str(e))

        # Store verified claims for downstream
        environ["JWT_PAYLOAD"] = payload
        return self.app(environ, start_response)

    def _unauthorized(self, start_response, message: str):
        body = json.dumps({"error": "unauthorized", "message": message}).encode()
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        start_response("401 Unauthorized", headers, None)
        return [body]
