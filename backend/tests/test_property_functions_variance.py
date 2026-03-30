"""Property test for compute_variance.

Feature: financial-domain-model
Property 11: compute_variance produces correct variance values
Validates: Requirements 6.3, 6.9
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from hypothesis import given, settings

from backend.app.core.domain import LineType
from backend.app.core.functions import compute_variance
from backend.tests.strategies import financial_documents

ZERO = Decimal("0")


@settings(max_examples=100)
@given(doc=financial_documents)
def test_variance_values_are_correct(doc):
    """variance_bva == actual - budget, variance_bvf == forecast - budget."""
    result = compute_variance(doc)

    # Build expected totals independently
    expected: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: ZERO),
    )
    for ln in doc.lines:
        key = (ln.account, ln.entity, ln.period)
        expected[key][ln.line_type] += ln.amount

    assert len(result) == len(expected)

    result_map = {(r.account, r.entity, r.period): r for r in result}
    for key, totals in expected.items():
        r = result_map[key]
        budget = totals.get(LineType.BUDGET, ZERO)
        actual = totals.get(LineType.ACTUAL, ZERO)
        forecast = totals.get(LineType.FORECAST, ZERO)
        assert r.budget == budget
        assert r.actual == actual
        assert r.forecast == forecast
        assert r.variance_bva == actual - budget
        assert r.variance_bvf == forecast - budget


@settings(max_examples=100)
@given(doc=financial_documents)
def test_variance_missing_line_types_default_to_zero(doc):
    """When a line_type is absent for a key, its amount is treated as 0."""
    result = compute_variance(doc)
    for r in result:
        # The identity must hold regardless of which line types were present
        assert r.variance_bva == r.actual - r.budget
        assert r.variance_bvf == r.forecast - r.budget
