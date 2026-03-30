# Feature: financial-domain-model, Property 3: FinancialDocument uses tuples for collection fields
# Validates: Requirements 1.7, 10.3
"""Property test: lines, accounts, entities are tuple (not list) for any valid FinancialDocument."""

from __future__ import annotations

from hypothesis import given, settings

from backend.app.core.domain import FinancialDocument
from backend.tests.strategies import financial_documents


@settings(max_examples=100)
@given(doc=financial_documents)
def test_financial_document_collections_are_tuples(doc: FinancialDocument) -> None:
    assert isinstance(doc.lines, tuple), f"lines is {type(doc.lines)}, expected tuple"
    assert isinstance(doc.accounts, tuple), (
        f"accounts is {type(doc.accounts)}, expected tuple"
    )
    assert isinstance(doc.entities, tuple), (
        f"entities is {type(doc.entities)}, expected tuple"
    )
