"""Property 18: API Response Consistency.

For any API endpoint call, response is valid JSON; success → 200,
client error → 400/422, not found → 404; all error responses have
non-empty ``detail``.

Validates: Requirements 17.1, 17.2, 17.3
"""

from __future__ import annotations

import json
import os
import tempfile

from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.persistence.config_store import ConfigStore
from backend.app.routers.configurations import set_store
from backend.app.templates.registry import _REGISTRY

_client = TestClient(app)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_all_packages = list(_REGISTRY.keys())
_all_pairs = [(pkg, tpl) for pkg, templates in _REGISTRY.items() for tpl in templates]

_safe_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=30,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_valid_json(resp) -> dict | list | None:
    """Assert the response body is valid JSON and return parsed value."""
    if resp.status_code == 204:
        return None
    body = resp.json()  # raises if not valid JSON
    return body


def _assert_error_has_detail(body: dict) -> None:
    """Assert that an error response body has a non-empty 'detail' field."""
    assert "detail" in body, f"Error response missing 'detail': {body}"
    assert body["detail"], f"Error response has empty 'detail': {body}"


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------


@settings(max_examples=10)
@given(data=st.data())
def test_get_packages_returns_200_json(data):
    """GET /api/templates/packages always returns 200 with valid JSON."""
    resp = _client.get("/api/templates/packages")
    assert resp.status_code == 200
    body = _assert_valid_json(resp)
    assert "packages" in body


@given(pair=st.sampled_from(_all_pairs))
@settings(max_examples=20)
def test_get_templates_valid_package_returns_200(pair):
    """GET templates for a valid package → 200 with JSON list."""
    pkg, _ = pair
    resp = _client.get(f"/api/templates/packages/{pkg}/templates")
    assert resp.status_code == 200
    body = _assert_valid_json(resp)
    assert "templates" in body


@given(pkg=_safe_text)
@settings(max_examples=30)
def test_get_templates_invalid_package_returns_404_with_detail(pkg: str):
    """GET templates for non-existent package → 404 with non-empty detail."""
    assume(pkg not in _REGISTRY)
    resp = _client.get(f"/api/templates/packages/{pkg}/templates")
    assert resp.status_code == 404
    body = _assert_valid_json(resp)
    _assert_error_has_detail(body)


@given(pair=st.sampled_from(_all_pairs))
@settings(max_examples=20)
def test_get_template_valid_returns_200(pair):
    """GET a valid package/template → 200 with JSON template."""
    pkg, tpl = pair
    resp = _client.get(f"/api/templates/packages/{pkg}/templates/{tpl}")
    assert resp.status_code == 200
    body = _assert_valid_json(resp)
    assert "template" in body


@given(pkg=_safe_text, tpl=_safe_text)
@settings(max_examples=30)
def test_get_template_invalid_returns_404_with_detail(pkg: str, tpl: str):
    """GET a non-existent package/template → 404 with non-empty detail."""
    assume(pkg not in _REGISTRY)
    resp = _client.get(f"/api/templates/packages/{pkg}/templates/{tpl}")
    assert resp.status_code == 404
    body = _assert_valid_json(resp)
    _assert_error_has_detail(body)


# ---------------------------------------------------------------------------
# Documentation endpoint
# ---------------------------------------------------------------------------


@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(data=st.data())
def test_documentation_incomplete_context_returns_400_with_detail(data):
    """POST /api/documentation/generate with empty context → 400 + detail."""
    resp = _client.post("/api/documentation/generate", json={})
    assert resp.status_code == 400
    body = _assert_valid_json(resp)
    _assert_error_has_detail(body)


@settings(max_examples=10)
@given(data=st.data())
def test_documentation_invalid_body_returns_422_with_detail(data):
    """POST /api/documentation/generate with non-object body → 422 + detail."""
    resp = _client.post(
        "/api/documentation/generate",
        content=json.dumps("not-an-object"),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    body = _assert_valid_json(resp)
    _assert_error_has_detail(body)


# ---------------------------------------------------------------------------
# Configuration endpoints
# ---------------------------------------------------------------------------


def _fresh_config_client() -> tuple[TestClient, str]:
    """Create a TestClient backed by a temporary DuckDB file."""
    tmp = tempfile.mktemp(suffix=".duckdb")
    store = ConfigStore(db_path=tmp)
    set_store(store)
    return TestClient(app), tmp


def _cleanup(path: str) -> None:
    for suffix in ("", ".wal"):
        try:
            os.unlink(path + suffix)
        except FileNotFoundError:
            pass


_config_name_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Pd"), whitelist_characters="_-"
    ),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() == s and len(s.strip()) > 0)


@given(
    name=_config_name_st,
    pkg=st.sampled_from(_all_packages),
    bc=_safe_text,
    yr=st.integers(min_value=2000, max_value=2100),
)
@settings(max_examples=30)
def test_config_create_returns_201_json(name: str, pkg: str, bc: str, yr: int):
    """POST /api/configurations with valid payload → 201 + valid JSON."""
    client, tmp = _fresh_config_client()
    try:
        payload = {
            "name": name,
            "packageName": pkg,
            "templateName": "budget",
            "budgetcode": bc,
            "year": yr,
        }
        resp = client.post("/api/configurations", json=payload)
        assert resp.status_code == 201
        body = _assert_valid_json(resp)
        assert body["name"] == name
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(name=_config_name_st)
@settings(max_examples=20)
def test_config_get_nonexistent_returns_404_with_detail(name: str):
    """GET /api/configurations/{name} for missing config → 404 + detail."""
    client, tmp = _fresh_config_client()
    try:
        resp = client.get(f"/api/configurations/{name}")
        assert resp.status_code == 404
        body = _assert_valid_json(resp)
        _assert_error_has_detail(body)
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(name=_config_name_st)
@settings(max_examples=20)
def test_config_update_nonexistent_returns_404_with_detail(name: str):
    """PUT /api/configurations/{name} for missing config → 404 + detail."""
    client, tmp = _fresh_config_client()
    try:
        resp = client.put(f"/api/configurations/{name}", json={"year": 2025})
        assert resp.status_code == 404
        body = _assert_valid_json(resp)
        _assert_error_has_detail(body)
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@given(name=_config_name_st)
@settings(max_examples=20)
def test_config_delete_nonexistent_returns_404_with_detail(name: str):
    """DELETE /api/configurations/{name} for missing config → 404 + detail."""
    client, tmp = _fresh_config_client()
    try:
        resp = client.delete(f"/api/configurations/{name}")
        assert resp.status_code == 404
        body = _assert_valid_json(resp)
        _assert_error_has_detail(body)
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@settings(max_examples=10)
@given(data=st.data())
def test_config_list_returns_200_json(data):
    """GET /api/configurations always returns 200 with valid JSON."""
    client, tmp = _fresh_config_client()
    try:
        resp = client.get("/api/configurations")
        assert resp.status_code == 200
        body = _assert_valid_json(resp)
        assert "configurations" in body
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)


@settings(max_examples=10)
@given(data=st.data())
def test_config_create_invalid_body_returns_422_with_detail(data):
    """POST /api/configurations with invalid body → 422 + detail."""
    client, tmp = _fresh_config_client()
    try:
        resp = client.post(
            "/api/configurations",
            content=json.dumps({"name": 123}),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
        body = _assert_valid_json(resp)
        _assert_error_has_detail(body)
    finally:
        set_store(None)  # type: ignore[arg-type]
        _cleanup(tmp)
