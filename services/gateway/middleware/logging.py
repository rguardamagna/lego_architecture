"""WSGI middleware: request logging."""
import logging
import sys
import time


class LoggingMiddleware:
    """Logs each request with method, path, status code, and duration."""

    def __init__(self, app, log_stream=None):
        self.app = app
        self.logger = logging.getLogger("gateway")
        if log_stream is not None:
            handler = logging.StreamHandler(log_stream)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            ))
            self.logger.handlers.clear()
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "?")
        path = environ.get("PATH_INFO", "/?")
        start = time.monotonic()

        status_codes = []

        def logging_start_response(status, headers, exc_info=None):
            status_codes.append(status.split()[0])
            return start_response(status, headers, exc_info)

        try:
            body = list(self.app(environ, logging_start_response))
        except Exception:
            elapsed = time.monotonic() - start
            self.logger.error(
                "%s %s -> 500 (%.3fs)",
                method, path, elapsed,
            )
            raise

        elapsed = time.monotonic() - start
        status = status_codes[0] if status_codes else "???"
        self.logger.info(
            "%s %s -> %s (%.3fs)",
            method, path, status, elapsed,
        )
        return body
