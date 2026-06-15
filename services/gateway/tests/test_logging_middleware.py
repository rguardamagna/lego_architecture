"""Tests for logging middleware."""
import io
import json
import re

from gateway.middleware.logging import LoggingMiddleware


def _simple_app(environ, start_response):
    """Minimal WSGI app returning hello."""
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"OK"]


class TestLoggingMiddleware:
    def test_logs_request_and_status(self):
        """Middleware debe loggear method, path y status."""
        buf = io.StringIO()
        app = LoggingMiddleware(_simple_app, log_stream=buf)
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/v1/auth/health",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.url_scheme": "http",
        }

        def start_response(status, headers, exc_info=None):
            pass

        list(app(environ, start_response))
        output = buf.getvalue()
        assert "GET" in output
        assert "/api/v1/auth/health" in output
        assert "200" in output

    def test_no_errors_on_exception(self):
        """Middleware no debe romperse si hay excepción en upstream."""
        buf = io.StringIO()
        app = LoggingMiddleware(_simple_app, log_stream=buf)
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/v1/auth/login",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.url_scheme": "http",
        }
        results = list(app(environ, lambda s, h, e=None: None))
        assert results == [b"OK"]
