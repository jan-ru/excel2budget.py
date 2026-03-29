"""Property 19: Environment Configuration Validation.

Validates Requirements 19.1, 19.2, 6.6:
- For any valid env var combination, Settings produces a matching config object.
- When env vars are absent, Settings uses documented defaults.
- When PORT is set to a non-integer value, Settings raises a validation error.
"""

from __future__ import annotations

import os

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from pydantic import ValidationError

from backend.app.settings import Settings, get_settings

VALID_LOG_LEVELS = ["debug", "info", "warning", "error"]

# Strategy for env-safe strings: printable, no null bytes, non-empty after strip
_env_safe_text = st.from_regex(r"[a-zA-Z0-9_./ -]{1,50}", fullmatch=True).filter(
    lambda s: len(s.strip()) > 0
)


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """Clear the lru_cache on get_settings before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSettingsDefaults:
    """When env vars are absent, Settings uses documented defaults."""

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch):
        for var in ("HOST", "PORT", "LOG_LEVEL", "DUCKDB_PATH"):
            monkeypatch.delenv(var, raising=False)

        s = Settings()
        assert s.host == "0.0.0.0"
        assert s.port == 8000
        assert s.log_level == "info"
        assert s.duckdb_path == "data/config.duckdb"

    def test_get_settings_returns_cached_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        for var in ("HOST", "PORT", "LOG_LEVEL", "DUCKDB_PATH"):
            monkeypatch.delenv(var, raising=False)

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2


class TestSettingsFromEnv:
    """For any valid env var combination, Settings produces matching config."""

    @settings(max_examples=100)
    @given(
        host=_env_safe_text,
        port=st.integers(min_value=1, max_value=65535),
        log_level=st.sampled_from(VALID_LOG_LEVELS),
        duckdb_path=_env_safe_text,
    )
    def test_valid_env_vars_produce_matching_config(
        self, host: str, port: int, log_level: str, duckdb_path: str
    ):
        env = {
            "HOST": host,
            "PORT": str(port),
            "LOG_LEVEL": log_level,
            "DUCKDB_PATH": duckdb_path,
        }
        old_env = {}
        for k, v in env.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            get_settings.cache_clear()
            s = Settings()
            assert s.host == host
            assert s.port == port
            assert s.log_level == log_level
            assert s.duckdb_path == duckdb_path
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class TestSettingsInvalidPort:
    """When PORT is set to a non-integer value, Settings raises ValidationError."""

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        bad_port=st.from_regex(r"[a-zA-Z!@#$%^&*()]+", fullmatch=True),
    )
    def test_non_integer_port_raises_validation_error(
        self, bad_port: str, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("PORT", bad_port)
        with pytest.raises(ValidationError):
            Settings()
