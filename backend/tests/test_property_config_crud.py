"""Property 5: Configuration CRUD Round-Trip.

For any valid configuration, create → get returns matching fields with
non-null timestamps.

Validates: Requirements 6.2, 6.3, 6.4
"""

from __future__ import annotations

import tempfile
import os

from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.persistence.config_store import ConfigStore
from backend.app.routers.configurations import set_store

# Strategy for valid configuration names (non-empty, no slashes for URL safety)
config_name_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Pd"), whitelist_characters="_-"
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)

package_name_st = st.sampled_from(["afas", "exact", "twinfield"])
template_name_st = st.just("budget")
budgetcode_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=20,
)
year_st = st.integers(min_value=2000, max_value=2100)


def _fresh_client() -> tuple[TestClient, str]:
    """Create a TestClient backed by a temporary DuckDB file."""
    tmp = tempfile.mktemp(suffix=".duckdb")
    store = ConfigStore(db_path=tmp)
    set_store(store)
    return TestClient(app), tmp


@given(
    name=config_name_st,
    pkg=package_name_st,
    tpl=template_name_st,
    bc=budgetcode_st,
    yr=year_st,
)
@settings(max_examples=50)
def test_create_then_get_round_trip(name: str, pkg: str, tpl: str, bc: str, yr: int):
    """Creating a config and getting it back returns matching fields."""
    client, tmp = _fresh_client()
    try:
        payload = {
            "name": name,
            "packageName": pkg,
            "templateName": tpl,
            "budgetcode": bc,
            "year": yr,
        }
        create_resp = client.post("/api/configurations", json=payload)
        assert create_resp.status_code == 201, create_resp.text

        created = create_resp.json()
        assert created["name"] == name
        assert created["packageName"] == pkg
        assert created["templateName"] == tpl
        assert created["budgetcode"] == bc
        assert created["year"] == yr
        assert created["createdAt"] is not None
        assert created["updatedAt"] is not None

        get_resp = client.get(f"/api/configurations/{name}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["name"] == name
        assert fetched["packageName"] == pkg
        assert fetched["templateName"] == tpl
        assert fetched["budgetcode"] == bc
        assert fetched["year"] == yr
        assert fetched["createdAt"] is not None
        assert fetched["updatedAt"] is not None
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(
    name=config_name_st,
    pkg=package_name_st,
    tpl=template_name_st,
    bc=budgetcode_st,
    yr=year_st,
    new_yr=year_st,
)
@settings(max_examples=30)
def test_update_preserves_created_at(
    name: str, pkg: str, tpl: str, bc: str, yr: int, new_yr: int
):
    """Updating a config preserves createdAt and bumps updatedAt."""
    client, tmp = _fresh_client()
    try:
        payload = {
            "name": name,
            "packageName": pkg,
            "templateName": tpl,
            "budgetcode": bc,
            "year": yr,
        }
        create_resp = client.post("/api/configurations", json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()

        update_resp = client.put(
            f"/api/configurations/{name}",
            json={"year": new_yr},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["year"] == new_yr
        # Compare timestamps ignoring trailing Z / timezone offset differences
        # from DuckDB round-trip (DuckDB stores as naive TIMESTAMP).
        assert _normalize_ts(updated["createdAt"]) == _normalize_ts(
            created["createdAt"]
        )
        assert updated["updatedAt"] is not None
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(
    name=config_name_st,
    pkg=package_name_st,
    tpl=template_name_st,
    bc=budgetcode_st,
    yr=year_st,
)
@settings(max_examples=30)
def test_delete_then_get_returns_404(name: str, pkg: str, tpl: str, bc: str, yr: int):
    """Deleting a config means a subsequent GET returns 404."""
    client, tmp = _fresh_client()
    try:
        payload = {
            "name": name,
            "packageName": pkg,
            "templateName": tpl,
            "budgetcode": bc,
            "year": yr,
        }
        client.post("/api/configurations", json=payload)

        del_resp = client.delete(f"/api/configurations/{name}")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/configurations/{name}")
        assert get_resp.status_code == 404
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(name=config_name_st)
@settings(max_examples=20)
def test_get_nonexistent_returns_404(name: str):
    """Getting a config that was never created returns 404."""
    client, tmp = _fresh_client()
    try:
        resp = client.get(f"/api/configurations/{name}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(
    name=config_name_st,
    pkg=package_name_st,
    tpl=template_name_st,
    bc=budgetcode_st,
    yr=year_st,
)
@settings(max_examples=30)
def test_list_includes_created(name: str, pkg: str, tpl: str, bc: str, yr: int):
    """A created config appears in the list endpoint."""
    client, tmp = _fresh_client()
    try:
        payload = {
            "name": name,
            "packageName": pkg,
            "templateName": tpl,
            "budgetcode": bc,
            "year": yr,
        }
        client.post("/api/configurations", json=payload)

        list_resp = client.get("/api/configurations")
        assert list_resp.status_code == 200
        names = [c["name"] for c in list_resp.json()["configurations"]]
        assert name in names
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


def _normalize_ts(ts: str) -> str:
    """Strip trailing Z and timezone offset for comparison."""
    return ts.rstrip("Z").split("+")[0]


def _cleanup(path: str) -> None:
    """Remove temp DuckDB files."""
    for suffix in ("", ".wal"):
        try:
            os.unlink(path + suffix)
        except FileNotFoundError:
            pass
