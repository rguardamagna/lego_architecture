"""WSGI middleware: CORS headers."""
class CORSMiddleware:
    """Adds CORS headers to responses and handles preflight OPTIONS."""

    def __init__(self, app, origins: str = "*"):
        self.app = app
        self.origins = origins

    def __call__(self, environ, start_response):
        if environ.get("REQUEST_METHOD") == "OPTIONS":
            return self._handle_preflight(start_response)

        return self._add_headers(environ, start_response)

    def _handle_preflight(self, start_response):
        headers = [
            ("Access-Control-Allow-Origin", self.origins),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-Id"),
            ("Access-Control-Max-Age", "86400"),
        ]
        start_response("204 No Content", headers, None)
        return [b""]

    def _add_headers(self, environ, start_response):
        cors_headers = [("Access-Control-Allow-Origin", self.origins)]

        def cors_start_response(status, headers, exc_info=None):
            headers.extend(cors_headers)
            return start_response(status, headers, exc_info)

        return self.app(environ, cors_start_response)
