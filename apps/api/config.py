"""API configuration via pydantic-settings."""

import os
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://sinal:sinal_dev@localhost:5432/sinal_dev"
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    # Newsletter (Resend)
    resend_api_key: str = ""
    resend_from_email: str = "news@sinal.tech"
    resend_audience_id: str = ""

    # AI
    anthropic_api_key: str = ""

    # Admin
    admin_emails: str = ""

    # Data Sources
    github_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def admin_emails_list(self) -> list[str]:
        if not self.admin_emails:
            return []
        return [e.strip().lower() for e in self.admin_emails.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
