# Feature: financial-domain-model, Property 7: Backend JSON serialization round-trip
# Validates: Requirements 8.1, 8.2, 8.3
"""Property test: model_validate_json(doc.model_dump_json()) == doc for all valid FinancialDocuments."""

from __future__ import annotations

from hypothesis import given, settings

from backend.app.core.domain import FinancialDocument
from backend.tests.strategies import financial_documents


@settings(max_examples=100)
@given(doc=financial_documents)
def test_json_round_trip(doc: FinancialDocument) -> None:
    json_str = doc.model_dump_json()
    restored = FinancialDocument.model_validate_json(json_str)
    assert restored == doc
