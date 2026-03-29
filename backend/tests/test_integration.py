"""Integration tests for the full backend API flows.

Tests cover:
1. Full pipeline flow: template retrieval for transformation support
2. Documentation generation: build ApplicationContext → POST → verify 7 artifacts
3. Configuration persistence: create → list → update → get → delete cycle

Requirements: 13.1, 5.1, 6.2
"""

from __future__ import annotations

import os
import tempfile

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.persistence.config_store import ConfigStore
from backend.app.routers.configurations import set_store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """TestClient with a fresh temporary DuckDB config store."""
    tmp = tempfile.mktemp(suffix=".duckdb")
    store = ConfigStore(db_path=tmp)
    set_store(store)
    try:
        yield TestClient(app)
    finally:
        store.close()
        set_store(None)  # type: ignore[arg-type]
        if os.path.exists(tmp):
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_application_context() -> dict:
    """Return a minimal but complete ApplicationContext payload."""
    return {
        "applicationName": "excel2budget",
        "configurationName": "afas budget 2026",
        "sourceSystem": {
            "name": "Excel",
            "systemType": "Spreadsheet",
            "description": "Budget file",
        },
        "targetSystem": {
            "name": "afas",
            "systemType": "Accounting Package",
            "description": "budget import",
        },
        "intermediarySystems": [],
        "processSteps": [
            {
                "stepNumber": 1,
                "name": "Upload",
                "description": "Upload budget file",
                "actor": "User",
            },
        ],
        "sourceDescription": {
            "name": "Budget Excel",
            "columns": [
                {
                    "name": "Entity",
                    "dataType": "STRING",
                    "description": "Entity column",
                    "source": "Mapping",
                },
            ],
            "additionalNotes": "",
        },
        "targetDescription": {
            "name": "Afas Budget Import",
            "columns": [
                {
                    "name": "AccountCode",
                    "dataType": "STRING",
                    "description": "Account code",
                    "source": "Source column: Account",
                },
            ],
            "additionalNotes": "",
        },
        "transformDescription": {
            "name": "Budget Unpivot",
            "description": "Unpivot + DC split",
            "steps": ["Unpivot months", "Split DC"],
            "generatedQuery": "SELECT * FROM budget",
        },
        "controlTotals": {
            "inputRowCount": 10,
            "outputRowCount": 120,
            "inputTotals": [{"label": "Budget Values", "value": 50000.0}],
            "outputTotals": [
                {"label": "Debet", "value": 30000.0},
                {"label": "Credit", "value": 20000.0},
            ],
            "balanceChecks": [
                {
                    "description": "Sum input = Sum Debet + Credit",
                    "passed": True,
                },
            ],
        },
        "userInstructionSteps": [
            "Upload your budget Excel file",
            "Select afas package",
        ],
    }


# ---------------------------------------------------------------------------
# 1. Full pipeline flow — template retrieval for transformation
# ---------------------------------------------------------------------------


class TestPipelineTemplateFlow:
    """Integration: list packages → list templates → get template → verify structure."""

    def test_list_packages_returns_all_three(self, client: TestClient):
        resp = client.get("/api/templates/packages")
        assert resp.status_code == 200
        packages = resp.json()["packages"]
        assert set(packages) == {"afas", "exact", "twinfield"}

    def test_list_templates_for_each_package(self, client: TestClient):
        for pkg in ("afas", "exact", "twinfield"):
            resp = client.get(f"/api/templates/packages/{pkg}/templates")
            assert resp.status_code == 200
            templates = resp.json()["templates"]
            assert "budget" in templates

    def test_get_template_returns_valid_output_template(self, client: TestClient):
        resp = client.get("/api/templates/packages/afas/templates/budget")
        assert resp.status_code == 200
        tpl = resp.json()["template"]
        assert tpl["packageName"] == "afas"
        assert tpl["templateName"] == "budget"
        assert len(tpl["columns"]) > 0
        # Every column has a sourceMapping with a type discriminator
        for col in tpl["columns"]:
            assert "sourceMapping" in col
            assert "type" in col["sourceMapping"]
            assert col["sourceMapping"]["type"] in (
                "from_source",
                "from_user_param",
                "from_transform",
                "fixed_null",
            )

    def test_full_template_retrieval_flow(self, client: TestClient):
        """Simulate the frontend flow: list packages → pick one → list templates → get template."""
        # Step 1: List packages
        pkgs_resp = client.get("/api/templates/packages")
        assert pkgs_resp.status_code == 200
        packages = pkgs_resp.json()["packages"]
        assert len(packages) >= 3

        # Step 2: Pick a package and list its templates
        pkg = "twinfield"
        tpls_resp = client.get(f"/api/templates/packages/{pkg}/templates")
        assert tpls_resp.status_code == 200
        templates = tpls_resp.json()["templates"]
        assert len(templates) >= 1

        # Step 3: Get the full template definition
        tpl_name = templates[0]
        detail_resp = client.get(f"/api/templates/packages/{pkg}/templates/{tpl_name}")
        assert detail_resp.status_code == 200
        template = detail_resp.json()["template"]
        assert template["packageName"] == pkg
        assert template["templateName"] == tpl_name
        assert isinstance(template["columns"], list)
        assert len(template["columns"]) > 0

    def test_invalid_package_returns_404_with_available(self, client: TestClient):
        resp = client.get("/api/templates/packages/nonexistent/templates")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
        assert len(body["available_packages"]) >= 3

    def test_invalid_template_returns_404_with_available(self, client: TestClient):
        resp = client.get("/api/templates/packages/afas/templates/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body
        assert "budget" in body["available_templates"]


# ---------------------------------------------------------------------------
# 2. Documentation generation — ApplicationContext → 7 artifacts
# ---------------------------------------------------------------------------


class TestDocumentationGeneration:
    """Integration: POST ApplicationContext → verify all 7 artifacts returned."""

    def test_valid_context_returns_all_seven_artifacts(self, client: TestClient):
        ctx = _valid_application_context()
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200
        pack = resp.json()

        # All 7 artifacts must be non-null
        assert pack["archimate"] is not None
        assert pack["bpmn"] is not None
        assert pack["inputDescription"] is not None
        assert pack["outputDescription"] is not None
        assert pack["transformDescription"] is not None
        assert pack["controlTable"] is not None
        assert pack["userInstruction"] is not None

    def test_archimate_diagram_structure(self, client: TestClient):
        ctx = _valid_application_context()
        resp = client.post("/api/documentation/generate", json=ctx)
        pack = resp.json()
        archimate = pack["archimate"]
        assert archimate["diagramType"] == "ARCHIMATE"
        assert len(archimate["renderedContent"]) > 0

    def test_bpmn_diagram_structure(self, client: TestClient):
        ctx = _valid_application_context()
        resp = client.post("/api/documentation/generate", json=ctx)
        pack = resp.json()
        bpmn = pack["bpmn"]
        assert bpmn["diagramType"] == "BPMN"
        assert len(bpmn["renderedContent"]) > 0

    def test_document_artifacts_have_content(self, client: TestClient):
        ctx = _valid_application_context()
        resp = client.post("/api/documentation/generate", json=ctx)
        pack = resp.json()

        for key in (
            "inputDescription",
            "outputDescription",
            "transformDescription",
            "userInstruction",
        ):
            artifact = pack[key]
            assert artifact["title"], f"{key} should have a title"
            assert artifact["content"], f"{key} should have content"
            assert artifact["contentType"], f"{key} should have a contentType"

    def test_control_table_has_totals(self, client: TestClient):
        ctx = _valid_application_context()
        resp = client.post("/api/documentation/generate", json=ctx)
        pack = resp.json()
        ct = pack["controlTable"]
        assert ct["totals"] is not None
        assert ct["totals"]["inputRowCount"] == 10
        assert ct["totals"]["outputRowCount"] == 120

    def test_incomplete_context_returns_400(self, client: TestClient):
        # Missing required fields
        resp = client.post("/api/documentation/generate", json={})
        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body
        assert "sourceSystem" in body["detail"]

    def test_partial_context_returns_400(self, client: TestClient):
        ctx = _valid_application_context()
        del ctx["controlTotals"]
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 400
        body = resp.json()
        assert "controlTotals" in body["detail"]

    def test_documentation_with_template_from_api(self, client: TestClient):
        """End-to-end: fetch template → build context with template info → generate docs."""
        # Fetch a real template
        tpl_resp = client.get("/api/templates/packages/afas/templates/budget")
        assert tpl_resp.status_code == 200
        template = tpl_resp.json()["template"]

        # Build context using template metadata
        ctx = _valid_application_context()
        ctx["targetDescription"]["name"] = (
            f"{template['packageName']} {template['templateName']} Import"
        )
        ctx["targetDescription"]["columns"] = [
            {
                "name": col["name"],
                "dataType": col["dataType"],
                "description": f"Target column: {col['name']}",
                "source": col["sourceMapping"]["type"],
            }
            for col in template["columns"]
        ]

        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200
        pack = resp.json()
        assert pack["archimate"] is not None
        assert pack["userInstruction"] is not None


# ---------------------------------------------------------------------------
# 3. Configuration persistence — full CRUD cycle
# ---------------------------------------------------------------------------


class TestConfigurationCRUD:
    """Integration: create → list → update → get → delete cycle."""

    def test_full_crud_cycle(self, client: TestClient):
        """Complete lifecycle: create → list → update → get → delete."""
        config_name = "test-config-crud"

        # CREATE
        create_resp = client.post(
            "/api/configurations",
            json={
                "name": config_name,
                "packageName": "afas",
                "templateName": "budget",
                "budgetcode": "BC001",
                "year": 2026,
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["name"] == config_name
        assert created["packageName"] == "afas"
        assert created["templateName"] == "budget"
        assert created["budgetcode"] == "BC001"
        assert created["year"] == 2026
        assert created["createdAt"] is not None
        assert created["updatedAt"] is not None

        # LIST — should contain the created config
        list_resp = client.get("/api/configurations")
        assert list_resp.status_code == 200
        configs = list_resp.json()["configurations"]
        names = [c["name"] for c in configs]
        assert config_name in names

        # UPDATE
        update_resp = client.put(
            f"/api/configurations/{config_name}",
            json={"budgetcode": "BC002", "year": 2027},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["budgetcode"] == "BC002"
        assert updated["year"] == 2027
        # Package and template should remain unchanged
        assert updated["packageName"] == "afas"
        assert updated["templateName"] == "budget"

        # GET — verify update persisted
        get_resp = client.get(f"/api/configurations/{config_name}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["budgetcode"] == "BC002"
        assert fetched["year"] == 2027

        # DELETE
        del_resp = client.delete(f"/api/configurations/{config_name}")
        assert del_resp.status_code == 204

        # GET after delete — should be 404
        get_after_del = client.get(f"/api/configurations/{config_name}")
        assert get_after_del.status_code == 404

    def test_create_duplicate_returns_409(self, client: TestClient):
        name = "dup-config"
        payload = {
            "name": name,
            "packageName": "exact",
            "templateName": "budget",
            "budgetcode": "DUP",
            "year": 2026,
        }
        resp1 = client.post("/api/configurations", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/configurations", json=payload)
        assert resp2.status_code == 409
        assert "already exists" in resp2.json()["detail"]

    def test_get_nonexistent_returns_404(self, client: TestClient):
        resp = client.get("/api/configurations/does-not-exist")
        assert resp.status_code == 404

    def test_update_nonexistent_returns_404(self, client: TestClient):
        resp = client.put(
            "/api/configurations/does-not-exist",
            json={"year": 2030},
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient):
        resp = client.delete("/api/configurations/does-not-exist")
        assert resp.status_code == 404

    def test_multiple_configs_listed(self, client: TestClient):
        """Create multiple configs and verify they all appear in the list."""
        for i in range(3):
            client.post(
                "/api/configurations",
                json={
                    "name": f"multi-{i}",
                    "packageName": "twinfield",
                    "templateName": "budget",
                    "budgetcode": f"MC{i}",
                    "year": 2026 + i,
                },
            )

        list_resp = client.get("/api/configurations")
        assert list_resp.status_code == 200
        configs = list_resp.json()["configurations"]
        names = {c["name"] for c in configs}
        assert {"multi-0", "multi-1", "multi-2"}.issubset(names)

    def test_partial_update_preserves_other_fields(self, client: TestClient):
        """Updating only one field should preserve all others."""
        name = "partial-update"
        client.post(
            "/api/configurations",
            json={
                "name": name,
                "packageName": "afas",
                "templateName": "budget",
                "budgetcode": "ORIG",
                "year": 2026,
            },
        )

        # Update only the year
        update_resp = client.put(
            f"/api/configurations/{name}",
            json={"year": 2030},
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["year"] == 2030
        assert updated["budgetcode"] == "ORIG"
        assert updated["packageName"] == "afas"
        assert updated["templateName"] == "budget"
