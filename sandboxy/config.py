"""Centralized configuration for Sandboxy.

All configuration is loaded from environment variables with SANDBOXY_ prefix.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="SANDBOXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    modules_dir: Path = Path("modules")
    agents_dir: Path = Path("agents")
    tools_dir: Path = Path("tools")

    # Security
    cors_origins: list[str] = Field(default_factory=list)
    allow_dynamic_tools: bool = True

    # HTTP Client
    http_timeout: float = 120.0

    # Runtime
    env: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the application configuration singleton."""
    return Config()


# Convenience alias
config = get_config()
