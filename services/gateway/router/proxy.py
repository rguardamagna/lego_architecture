"""HTTP proxy for forwarding requests to upstream services."""
import json
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError


def proxy_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes,
    timeout: int = 30,
) -> tuple[int, dict[str, str], bytes]:
    """Forward an HTTP request to an upstream service.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Full upstream URL.
        headers: Request headers to forward.
        body: Raw request body.
        timeout: Upstream connection timeout in seconds.

    Returns:
        Tuple of (status_code, response_headers_dict, response_body_bytes).
    """
    # Inject headers
    if "X-Request-Id" not in headers and "x-request-id" not in headers:
        headers["X-Request-Id"] = str(uuid.uuid4())
    if "X-Forwarded-For" not in headers and "x-forwarded-for" not in headers:
        headers["X-Forwarded-For"] = "127.0.0.1"

    req = Request(url, data=body or None, headers=headers, method=method)

    try:
        resp = urlopen(req, timeout=timeout)
        resp_headers = dict(resp.headers)
        resp_body = resp.read()
        return resp.status, resp_headers, resp_body
    except URLError as e:
        status = 502
        error_body = json.dumps({
            "error": "bad_gateway",
            "message": f"Upstream connection failed: {e.reason}",
        }).encode()
        return status, {"Content-Type": "application/json"}, error_body
