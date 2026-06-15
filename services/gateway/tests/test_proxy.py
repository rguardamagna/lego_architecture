"""Tests for gateway proxy."""
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest
from gateway.router.proxy import proxy_request


class MockUpstreamHandler(BaseHTTPRequestHandler):
    """Simple HTTP server that echoes method, path, headers, and body."""

    def _respond(self, status: int, data: dict):
        content = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        self._respond(200, {
            "method": "GET",
            "path": self.path,
            "headers": dict(self.headers),
        })

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self._respond(201, {
            "method": "POST",
            "path": self.path,
            "body": body.decode(),
            "headers": dict(self.headers),
        })

    def do_DELETE(self):
        self.send_response(204)
        self.end_headers()

    def do_GET_error(self):
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":"internal"}')

    def log_message(self, format, *args):
        pass  # Silence logs


@pytest.fixture(scope="module")
def upstream_server():
    """Start a mock upstream server on a random port."""
    server = HTTPServer(("127.0.0.1", 0), MockUpstreamHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)  # Give it a moment to start
    yield port
    server.shutdown()


class TestProxy:
    def test_get_request(self, upstream_server):
        """GET request should return 200 with correct body."""
        url = f"http://127.0.0.1:{upstream_server}/api/v1/users/me"
        status, headers, body = proxy_request("GET", url, {}, b"")
        assert status == 200
        data = json.loads(body)
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/users/me"

    def test_post_request(self, upstream_server):
        """POST should forward body and return 201."""
        url = f"http://127.0.0.1:{upstream_server}/api/v1/auth/register"
        payload = json.dumps({"email": "test@test.com"}).encode()
        status, headers, body = proxy_request("POST", url, {}, payload)
        assert status == 201
        data = json.loads(body)
        assert data["method"] == "POST"
        assert data["body"] == '{"email": "test@test.com"}'

    def test_delete_request(self, upstream_server):
        """DELETE should return 204."""
        url = f"http://127.0.0.1:{upstream_server}/api/v1/resource/1"
        status, _, _ = proxy_request("DELETE", url, {}, b"")
        assert status == 204

    def test_connection_refused_returns_502(self):
        """Connection to unreachable host should return 502."""
        status, _, body = proxy_request("GET", "http://127.0.0.1:1/nonexistent", {}, b"")
        assert status == 502
        data = json.loads(body)
        assert "error" in data
        assert data["error"] == "bad_gateway"

    def test_x_request_id_is_added(self, upstream_server):
        """X-Request-Id header should be injected if not present."""
        url = f"http://127.0.0.1:{upstream_server}/test"
        _, _, body = proxy_request("GET", url, {}, b"")
        data = json.loads(body)
        echo_headers = data.get("headers", {})
        rid = echo_headers.get("X-Request-Id") or echo_headers.get("x-request-id")
        assert rid is not None, f"X-Request-Id not found in echoed headers: {echo_headers}"

    def test_x_forwarded_for_is_added(self, upstream_server):
        """X-Forwarded-For header should be injected."""
        url = f"http://127.0.0.1:{upstream_server}/test"
        _, _, body = proxy_request("GET", url, {}, b"")
        data = json.loads(body)
        echo_headers = data.get("headers", {})
        forwarded = echo_headers.get("X-Forwarded-For") or echo_headers.get("x-forwarded-for")
        assert forwarded == "127.0.0.1"
