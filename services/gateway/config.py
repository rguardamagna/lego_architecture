"""Gateway configuration via pydantic-settings."""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables with GATEWAY_ prefix."""

    port: int = 8080
    jwt_secret: str = "dev-secret-do-not-use-in-prod"
    jwt_preverify: bool = True
    cors_origins: str = "*"
    log_level: str = "INFO"
    upstream_timeout: int = 30

    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env")

    @property
    def route_map(self) -> dict[str, str]:
        """Build route map from GATEWAY_ROUTE_* env vars.

        Matches any env var named GATEWAY_ROUTE_<NAME>, normalizing
        NAME to uppercase for the route key.
        """
        prefix = "GATEWAY_ROUTE_"
        routes: dict[str, str] = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                name = key[len(prefix):].upper()
                routes[name] = value
        return routes
