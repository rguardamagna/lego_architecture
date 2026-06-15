"""Configuración de la app vía pydantic-settings."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./auth.db"
    jwt_secret: str
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    cors_origins: str = "*"
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_prefix = "AUTH_"
        env_file = ".env"
