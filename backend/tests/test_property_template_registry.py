"""Property 2: Template Registry API Round-Trip.

For any registered package/template, list-packages includes the package,
list-templates includes the template, get-template returns matching
OutputTemplate.

Validates: Requirements 4.1, 4.2, 4.3
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.templates.registry import _REGISTRY

_client = TestClient(app)

_all_packages = list(_REGISTRY.keys())
_all_pairs = [(pkg, tpl) for pkg, templates in _REGISTRY.items() for tpl in templates]

package_strategy = st.sampled_from(_all_packages)
pair_strategy = st.sampled_from(_all_pairs)


@given(pkg=package_strategy)
@settings(max_examples=20)
def test_list_packages_includes_registered(pkg: str):
    """list-packages always includes every registered package."""
    resp = _client.get("/api/templates/packages")
    assert resp.status_code == 200
    assert pkg in resp.json()["packages"]


@given(data=pair_strategy)
@settings(max_examples=20)
def test_list_templates_includes_registered(data):
    """list-templates includes the registered template."""
    pkg, tpl = data
    resp = _client.get(f"/api/templates/packages/{pkg}/templates")
    assert resp.status_code == 200
    assert tpl in resp.json()["templates"]


@given(data=pair_strategy)
@settings(max_examples=20)
def test_get_template_returns_matching(data):
    """get-template returns OutputTemplate matching the registry."""
    pkg, tpl = data
    resp = _client.get(f"/api/templates/packages/{pkg}/templates/{tpl}")
    assert resp.status_code == 200
    template = resp.json()["template"]
    assert template["packageName"] == pkg
    assert template["templateName"] == tpl

    expected = _REGISTRY[pkg][tpl]
    assert len(template["columns"]) == len(expected.columns)

    for actual_col, expected_col in zip(template["columns"], expected.columns):
        assert actual_col["name"] == expected_col.name
        assert actual_col["dataType"] == expected_col.dataType.value
        assert actual_col["nullable"] == expected_col.nullable
