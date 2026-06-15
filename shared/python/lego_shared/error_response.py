"""Standard error response contract."""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ErrorResponse:
    """Formato de error estándar para toda la API."""

    error: str
    message: str
    detail: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
