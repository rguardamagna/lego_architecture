"""Email value object."""
import re
from dataclasses import dataclass

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email:
    """Email validated and normalized to lowercase."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email: {self.value!r}")
        # Normalizar a lowercase
        object.__setattr__(self, "value", self.value.lower())

    def __repr__(self) -> str:
        return f"Email({self.value})"
