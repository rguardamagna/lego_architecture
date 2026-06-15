"""E2E smoke test: run gateway in Docker, verify health endpoint."""
import os
import subprocess
import time
import urllib.request
import urllib.error
import json
import pytest


GATEWAY_PORT = 18080
IMAGE_TAG = "lego-gateway-e2e"
GATEWAY_NAME = "lego-gateway-e2e"

pytestmark = pytest.mark.skipif(
    os.system("docker info > /dev/null 2>&1") != 0,
    reason="Docker daemon not available",
)


@pytest.fixture(scope="module")
def gateway_container():
    """Build Docker image and run gateway container."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
    )

    # Build
    print(f"Building image {IMAGE_TAG} from {repo_root}...")
    subprocess.run(
        ["docker", "build", "-f", "Dockerfile.gateway", "-t", IMAGE_TAG, "."],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )

    # Start container
    print(f"Starting container {GATEWAY_NAME}...")
    container = subprocess.run(
        [
            "docker", "run", "--rm", "-d",
            "--name", GATEWAY_NAME,
            "-p", f"{GATEWAY_PORT}:8080",
            "-e", "GATEWAY_JWT_SECRET=e2e-test-secret",
            "-e", "GATEWAY_JWT_PREVERIFY=true",
            "-e", "GATEWAY_LOG_LEVEL=DEBUG",
            IMAGE_TAG,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = container.stdout.strip()

    # Wait for readiness
    url = f"http://localhost:{GATEWAY_PORT}/health"
    for attempt in range(20):
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                print(f"Gateway ready after {attempt + 1}s")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        # Clean up if never ready
        subprocess.run(["docker", "kill", container_id], capture_output=True)
        pytest.fail("Gateway did not become ready within 20s")

    yield container_id

    # Cleanup
    print(f"Stopping container {container_id}...")
    subprocess.run(["docker", "kill", container_id], capture_output=True)


class TestE2ESmoke:
    def test_health_returns_200(self, gateway_container):
        """GET /health returns 200 with healthy status."""
        resp = urllib.request.urlopen(f"http://localhost:{GATEWAY_PORT}/health")
        assert resp.status == 200
        data = json.loads(resp.read())
        assert data["status"] == "healthy"
        assert data["service"] == "gateway"

    def test_health_content_type(self, gateway_container):
        """/health returns application/json."""
        resp = urllib.request.urlopen(f"http://localhost:{GATEWAY_PORT}/health")
        assert resp.headers.get("Content-Type") == "application/json"

    def test_unknown_route_returns_404(self, gateway_container):
        """GET /api/v1/unknown returns 404."""
        try:
            resp = urllib.request.urlopen(
                f"http://localhost:{GATEWAY_PORT}/api/v1/nonexistent"
            )
        except urllib.error.HTTPError as e:
            assert e.code == 404
            data = json.loads(e.read())
            assert "error" in data
        else:
            pytest.fail("Expected 404")

    def test_cors_headers_present(self, gateway_container):
        """Response includes Access-Control-Allow-Origin."""
        resp = urllib.request.urlopen(f"http://localhost:{GATEWAY_PORT}/health")
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_preflight_succeeds(self, gateway_container):
        """OPTIONS /health returns 204 with CORS."""
        req = urllib.request.Request(
            f"http://localhost:{GATEWAY_PORT}/health",
            method="OPTIONS",
        )
        resp = urllib.request.urlopen(req)
        assert resp.status == 204
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
