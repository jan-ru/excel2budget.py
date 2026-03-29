"""Shared test fixtures for the backend test suite.

Ensures that:
- ``get_settings`` lru_cache is cleared before/after each test so env
  changes take effect.
- ``DUCKDB_PATH`` points to a temporary file so the lifespan handler
  never creates files at the production default path.
- A ready-to-use ``TestClient`` fixture is available for tests that need
  the full app with lifespan-managed ``config_store``.
"""

from __future__ import annotations

import os

import pytest

from backend.app.settings import get_settings


@pytest.fixture(autouse=True)
def _settings_env(tmp_path):
    """Set DUCKDB_PATH to a temp file and clear the settings cache.

    This is **autouse** so every test automatically gets a clean settings
    environment.  The lifespan handler (which calls ``get_settings()``)
    will pick up the temporary path instead of the production default.
    """
    tmp_db = str(tmp_path / "test.duckdb")
    old_val = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = tmp_db
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    if old_val is None:
        os.environ.pop("DUCKDB_PATH", None)
    else:
        os.environ["DUCKDB_PATH"] = old_val
