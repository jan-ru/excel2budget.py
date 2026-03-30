"""Property tests for filter_entity and filter_period.

Feature: financial-domain-model
Property 9: filter_entity returns only matching lines and preserves metadata
Property 10: filter_period returns only matching year lines
Validates: Requirements 6.1, 6.2, 6.8
"""

from __future__ import annotations

from hypothesis import given, settings

from backend.app.core.functions import filter_entity, filter_period
from backend.tests.strategies import entity_codes, financial_documents


# ---------------------------------------------------------------------------
# Property 9 — filter_entity
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(doc=financial_documents, entity=entity_codes)
def test_filter_entity_returns_only_matching_lines(doc, entity):
    """Every line in the result has the requested entity."""
    result = filter_entity(doc, entity)
    for ln in result.lines:
        assert ln.entity == entity


@settings(max_examples=100)
@given(doc=financial_documents, entity=entity_codes)
def test_filter_entity_preserves_metadata(doc, entity):
    """accounts, entities, and meta are unchanged."""
    result = filter_entity(doc, entity)
    assert result.accounts == doc.accounts
    assert result.entities == doc.entities
    assert result.meta == doc.meta


@settings(max_examples=100)
@given(doc=financial_documents, entity=entity_codes)
def test_filter_entity_does_not_drop_matching_lines(doc, entity):
    """All matching lines from the original appear in the result."""
    result = filter_entity(doc, entity)
    expected = [ln for ln in doc.lines if ln.entity == entity]
    assert list(result.lines) == expected


# ---------------------------------------------------------------------------
# Property 10 — filter_period
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(doc=financial_documents)
def test_filter_period_returns_only_matching_year(doc):
    """Every line in the result has a period starting with the requested year."""
    year = 2025
    result = filter_period(doc, year)
    for ln in result.lines:
        assert ln.period.startswith(str(year))


@settings(max_examples=100)
@given(doc=financial_documents)
def test_filter_period_does_not_drop_matching_lines(doc):
    """All matching lines from the original appear in the result."""
    year = 2025
    result = filter_period(doc, year)
    expected = [ln for ln in doc.lines if ln.period.startswith(str(year))]
    assert list(result.lines) == expected
