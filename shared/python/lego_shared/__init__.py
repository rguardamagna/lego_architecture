"""lego_shared package."""
from .logging import setup_logging
from .health import build_health_response
from .error_response import ErrorResponse

__all__ = ["setup_logging", "build_health_response", "ErrorResponse"]
