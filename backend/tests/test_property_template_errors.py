"""Property 3: Template API Error on Invalid Lookup.

For any non-existent package, the API returns error with available packages;
for valid package but non-existent template, returns error with available
templates.

Validates: Requirements 4.4
"""

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.templates.registry import _REGISTRY

_all_packages = list(_REGISTRY.keys())
_all_templates_by_pkg = {
    pkg: list(templates.keys()) for pkg, templates in _REGISTRY.items()
}

invalid_package_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=30,
).filter(lambda s: s not in _REGISTRY)

valid_package_strategy = st.sampled_from(_all_packages)


@pytest.fixture()
def client():
    """TestClient created after conftest sets DUCKDB_PATH."""
    with TestClient(app) as c:
        yield c


class TestTemplateErrors:
    """Template API error responses for invalid lookups."""

    @given(pkg=invalid_package_strategy)
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_invalid_package_returns_error_with_available(self, pkg, client):
        """Non-existent package → 404 with available_packages."""
        resp = client.get(f"/api/templates/packages/{pkg}/templates")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]
        assert set(body["available_packages"]) == set(_all_packages)

    @given(
        pkg=valid_package_strategy,
        tpl=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_invalid_template_returns_error_with_available(self, pkg, tpl, client):
        """Valid package + non-existent template → 404 with available_templates."""
        assume(tpl not in _all_templates_by_pkg[pkg])
        resp = client.get(f"/api/templates/packages/{pkg}/templates/{tpl}")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]
        assert set(body["available_templates"]) == set(_all_templates_by_pkg[pkg])

    @given(pkg=invalid_package_strategy)
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_invalid_package_get_template_returns_error(self, pkg, client):
        """Non-existent package on get-template → 404 with available_packages."""
        resp = client.get(f"/api/templates/packages/{pkg}/templates/anything")
        assert resp.status_code == 404
        body = resp.json()
        assert set(body["available_packages"]) == set(_all_packages)
