"""BCrypt password hasher adapter."""
import bcrypt
from domain.ports.password_hasher import PasswordHasher


class BCryptPasswordHasher(PasswordHasher):
    """Implements PasswordHasher using bcrypt."""

    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
