"""Property 4: Documentation Generation Completeness.

For any valid ApplicationContext with all required fields, the response
contains all 7 non-null artifacts.

Validates: Requirements 5.1, 5.3
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from starlette.testclient import TestClient

from backend.app.main import app

# --- Strategies for building a valid ApplicationContext ---

_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"), whitelist_characters="_-"
    ),
    min_size=1,
    max_size=40,
)

system_descriptor_st = st.fixed_dictionaries(
    {
        "name": _safe_text,
        "systemType": _safe_text,
        "description": _safe_text,
    }
)

process_step_st = st.fixed_dictionaries(
    {
        "stepNumber": st.integers(min_value=1, max_value=20),
        "name": _safe_text,
        "description": _safe_text,
        "actor": _safe_text,
    }
)

column_description_st = st.fixed_dictionaries(
    {
        "name": _safe_text,
        "dataType": _safe_text,
        "description": _safe_text,
        "source": _safe_text,
    }
)

data_description_st = st.fixed_dictionaries(
    {
        "name": _safe_text,
        "columns": st.lists(column_description_st, min_size=1, max_size=5),
        "additionalNotes": _safe_text,
    }
)

transform_descriptor_st = st.fixed_dictionaries(
    {
        "name": _safe_text,
        "description": _safe_text,
        "steps": st.lists(_safe_text, min_size=1, max_size=5),
        "generatedQuery": _safe_text,
    }
)

named_total_st = st.fixed_dictionaries(
    {
        "label": _safe_text,
        "value": st.floats(
            min_value=0, max_value=1e9, allow_nan=False, allow_infinity=False
        ),
    }
)

balance_check_st = st.fixed_dictionaries(
    {
        "description": _safe_text,
        "passed": st.booleans(),
    }
)

control_totals_st = st.fixed_dictionaries(
    {
        "inputRowCount": st.integers(min_value=0, max_value=10000),
        "outputRowCount": st.integers(min_value=0, max_value=10000),
        "inputTotals": st.lists(named_total_st, min_size=1, max_size=3),
        "outputTotals": st.lists(named_total_st, min_size=1, max_size=3),
        "balanceChecks": st.lists(balance_check_st, min_size=1, max_size=3),
    }
)

valid_context_st = st.fixed_dictionaries(
    {
        "applicationName": _safe_text,
        "configurationName": _safe_text,
        "sourceSystem": system_descriptor_st,
        "targetSystem": system_descriptor_st,
        "intermediarySystems": st.lists(system_descriptor_st, max_size=2),
        "processSteps": st.lists(process_step_st, min_size=1, max_size=6),
        "sourceDescription": data_description_st,
        "targetDescription": data_description_st,
        "transformDescription": transform_descriptor_st,
        "controlTotals": control_totals_st,
        "userInstructionSteps": st.lists(_safe_text, min_size=1, max_size=5),
    }
)


@pytest.fixture()
def client():
    """TestClient created after conftest sets DUCKDB_PATH."""
    with TestClient(app) as c:
        yield c


class TestDocumentationCompleteness:
    """Documentation generation completeness properties."""

    @given(ctx=valid_context_st)
    @settings(
        max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_all_seven_artifacts_present(self, ctx: dict, client):
        """A valid ApplicationContext produces all 7 non-null artifacts."""
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["archimate"] is not None
        assert body["bpmn"] is not None
        assert body["inputDescription"] is not None
        assert body["outputDescription"] is not None
        assert body["transformDescription"] is not None
        assert body["controlTable"] is not None
        assert body["userInstruction"] is not None
        assert body["generatedAt"] is not None

    @given(ctx=valid_context_st)
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_archimate_is_archimate_type(self, ctx: dict, client):
        """The archimate artifact has diagramType ARCHIMATE."""
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200
        assert resp.json()["archimate"]["diagramType"] == "ARCHIMATE"

    @given(ctx=valid_context_st)
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_bpmn_is_bpmn_type(self, ctx: dict, client):
        """The bpmn artifact has diagramType BPMN."""
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200
        assert resp.json()["bpmn"]["diagramType"] == "BPMN"

    @given(ctx=valid_context_st)
    @settings(
        max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_artifacts_have_nonempty_content(self, ctx: dict, client):
        """All text-based artifacts have non-empty content."""
        resp = client.post("/api/documentation/generate", json=ctx)
        assert resp.status_code == 200
        body = resp.json()

        assert body["archimate"]["renderedContent"] != ""
        assert body["bpmn"]["renderedContent"] != ""
        assert body["inputDescription"]["content"] != ""
        assert body["outputDescription"]["content"] != ""
        assert body["transformDescription"]["content"] != ""
        assert body["userInstruction"]["content"] != ""

    def test_incomplete_context_returns_400(self, client):
        """An empty ApplicationContext returns 400 with descriptive error."""
        resp = client.post("/api/documentation/generate", json={})
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "sourceSystem" in detail
        assert "targetSystem" in detail
        assert "processSteps" in detail

    def test_partial_context_returns_400(self, client):
        """A context with only some fields returns 400 listing missing ones."""
        partial = {
            "sourceSystem": {
                "name": "Excel",
                "systemType": "file",
                "description": "src",
            },
            "targetSystem": {"name": "Afas", "systemType": "erp", "description": "tgt"},
        }
        resp = client.post("/api/documentation/generate", json=partial)
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "processSteps" in detail
        assert "sourceDescription" in detail
