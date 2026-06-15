"""Tests for CORS middleware."""
from gateway.middleware.cors import CORSMiddleware


def _simple_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")], None)
    return [b"OK"]


class TestCORSMiddleware:
    def test_adds_cors_headers(self):
        """Middleware debe agregar CORS headers a respuestas normales."""
        app = CORSMiddleware(_simple_app, origins="*")
        headers = []

        def start_response(status, hdrs, exc_info=None):
            headers.extend(hdrs)
            return None

        list(app({"REQUEST_METHOD": "GET"}, start_response))
        header_dict = dict(headers)
        assert header_dict.get("Access-Control-Allow-Origin") == "*"

    def test_preflight_returns_204(self):
        """OPTIONS request debe retornar 204 con CORS headers."""
        app = CORSMiddleware(_simple_app, origins="*")
        headers = []
        status_code = []

        def start_response(status, hdrs, exc_info=None):
            status_code.append(status)
            headers.extend(hdrs)
            return None

        body = list(app({"REQUEST_METHOD": "OPTIONS"}, start_response))
        assert status_code[0] == "204 No Content"
        assert body == [b""]

    def test_preflight_has_cors_headers(self):
        """OPTIONS debe incluir Allow-Methods y Allow-Headers."""
        app = CORSMiddleware(_simple_app, origins="*")
        headers = []

        def start_response(status, hdrs, exc_info=None):
            headers.extend(hdrs)
            return None

        list(app({"REQUEST_METHOD": "OPTIONS"}, start_response))
        header_dict = dict(headers)
        assert "Access-Control-Allow-Methods" in header_dict
        assert "Access-Control-Allow-Headers" in header_dict

    def test_custom_origin(self):
        """CORS debe aceptar origin custom."""
        app = CORSMiddleware(_simple_app, origins="https://example.com")
        headers = []

        def start_response(status, hdrs, exc_info=None):
            headers.extend(hdrs)
            return None

        list(app({"REQUEST_METHOD": "GET"}, start_response))
        assert dict(headers).get("Access-Control-Allow-Origin") == "https://example.com"
