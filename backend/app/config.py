"""
TaskFlow Application Configuration Module
-----------------------------------------
Loads configuration from environment variables with local .env support
using Pydantic Settings (Pydantic v2).
"""

from functools import lru_cache
from typing import List, Set

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, type-safe application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = Field(default="TaskFlow", description="Application service name")
    APP_ENV: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    HOST: str = Field(default="0.0.0.0", description="Bind host")
    PORT: int = Field(default=8000, description="Bind port")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./taskflow.db",
        description="SQLAlchemy relational database connection string",
    )

    # In-Memory Cache & Message Broker (Redis)
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate limiting",
    )

    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated allowed origins for CORS",
    )

    # Security & Reverse Proxy
    TRUSTED_PROXIES: str = Field(
        default="127.0.0.1,::1,localhost,testclient",
        description="Comma-separated IPs of trusted reverse proxies",
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Standard logging level")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a trimmed list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_proxies_set(self) -> Set[str]:
        """Parse comma-separated trusted proxies into a trimmed set."""
        return {p.strip() for p in self.TRUSTED_PROXIES.split(",") if p.strip()}


@lru_cache()
def get_settings() -> Settings:
    """FastAPI dependency and cached singleton for application settings."""
    return Settings()


# Default singleton instance for direct module imports
settings = get_settings()
