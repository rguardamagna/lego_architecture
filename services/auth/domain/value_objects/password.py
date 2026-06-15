"""Password value object and policy."""
import re
from dataclasses import dataclass

import bcrypt


class PasswordPolicy:
    """Validates password strength."""

    MIN_LENGTH = 8
    UPPERCASE_RE = re.compile(r"[A-Z]")
    LOWERCASE_RE = re.compile(r"[a-z]")
    DIGIT_RE = re.compile(r"\d")
    SPECIAL_RE = re.compile(r'[!@#$%^&*(),.?":{}|<>_\-]')

    @classmethod
    def validate(cls, plain: str) -> bool:
        """Returns True if password meets all criteria."""
        if len(plain) < cls.MIN_LENGTH:
            return False
        if not cls.UPPERCASE_RE.search(plain):
            return False
        if not cls.LOWERCASE_RE.search(plain):
            return False
        if not cls.DIGIT_RE.search(plain):
            return False
        if not cls.SPECIAL_RE.search(plain):
            return False
        return True


@dataclass(frozen=True)
class PasswordHash:
    """Password hash using bcrypt."""

    value: str

    @classmethod
    def from_plain(cls, plain: str) -> "PasswordHash":
        """Hash a plain text password."""
        hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
        return cls(hashed.decode("utf-8"))

    def verify(self, plain: str) -> bool:
        """Verify a plain text password against the hash."""
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), self.value.encode("utf-8"))
        except (ValueError, TypeError):
            return False
