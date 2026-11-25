from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://stories:stories@localhost:5432/stories"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    auth_username: str = "admin"
    auth_password: str = "admin"
    app_public_base_url: str = "http://localhost:8000"
    app_timezone: str = "America/Bogota"
    media_dir: Path = Path("media")
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )

    ig_access_token: str = ""
    ig_user_id: str = ""
    ig_graph_host: str = "https://graph.facebook.com"
    ig_graph_version: str = "v22.0"
    ig_app_id: str = ""
    ig_app_secret: str = ""

    publishing_limit_fallback: int = 100
    worker_interval_seconds: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def insecure_defaults(self) -> list[str]:
        """Nombres de las variables que siguen con valores de fábrica inseguros."""
        found = []
        if self.auth_password in {"", "admin"}:
            found.append("AUTH_PASSWORD")
        if self.jwt_secret in {"", "change-me"}:
            found.append("JWT_SECRET")
        return found


@lru_cache
def get_settings() -> Settings:
    return Settings()
