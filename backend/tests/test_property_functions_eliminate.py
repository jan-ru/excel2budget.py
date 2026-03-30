"""Property test for eliminate_intercompany.

Feature: financial-domain-model
Property 12: eliminate_intercompany removes elimination entity lines
Validates: Requirements 6.4
"""

from __future__ import annotations

from hypothesis import given, settings

from backend.app.core.functions import eliminate_intercompany
from backend.tests.strategies import entity_codes, financial_documents


@settings(max_examples=100)
@given(doc=financial_documents, elim=entity_codes)
def test_no_elimination_entity_lines_remain(doc, elim):
    """After elimination, no line has the elimination entity."""
    result = eliminate_intercompany(doc, elim)
    for ln in result.lines:
        assert ln.entity != elim


@settings(max_examples=100)
@given(doc=financial_documents, elim=entity_codes)
def test_non_elimination_lines_preserved(doc, elim):
    """Lines not matching the elimination entity are kept intact."""
    result = eliminate_intercompany(doc, elim)
    expected = [ln for ln in doc.lines if ln.entity != elim]
    assert list(result.lines) == expected
