"""Centralized configuration via environment variables (12-Factor: Config).

All runtime configuration is read from environment variables with sensible
defaults.  Invalid values (e.g. ``PORT=abc``) raise a ``ValidationError``
at startup, preventing the application from running with bad configuration.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings populated from environment variables."""

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    duckdb_path: str = "data/config.duckdb"

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance (singleton)."""
    return Settings()
