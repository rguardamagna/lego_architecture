"""Health check response builder."""
from datetime import datetime, timezone
from typing import Any


def build_health_response(
    service: str,
    version: str = "0.1.0",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye respuesta estándar de health check."""
    response: dict[str, Any] = {
        "status": "healthy",
        "service": service,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        response.update(extra)
    return response
