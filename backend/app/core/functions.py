"""Pure function layer for FinancialDocument operations.

All functions are stateless and side-effect-free.
They accept a ``FinancialDocument`` and return a new one (or derived data).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from backend.app.core.domain import (
    EntityCode,
    FinancialDocument,
    IncomeStatementLine,
    LineType,
)

ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_entity(doc: FinancialDocument, entity: EntityCode) -> FinancialDocument:
    """Return a new document with only lines matching *entity*.

    ``accounts``, ``entities``, and ``meta`` are preserved unchanged.
    """
    return doc.model_copy(
        update={
            "lines": tuple(ln for ln in doc.lines if ln.entity == entity),
        },
    )


def filter_period(doc: FinancialDocument, year: int) -> FinancialDocument:
    """Return a new document with only lines whose period starts with *year*."""
    prefix = str(year)
    return doc.model_copy(
        update={
            "lines": tuple(ln for ln in doc.lines if ln.period.startswith(prefix)),
        },
    )


# ---------------------------------------------------------------------------
# Variance computation
# ---------------------------------------------------------------------------


def compute_variance(doc: FinancialDocument) -> list[IncomeStatementLine]:
    """Group lines by (account, entity, period), sum by line_type, compute variances.

    Missing line types default to ``Decimal("0")``.
    Returns one ``IncomeStatementLine`` per unique (account, entity, period) key.
    """
    groups: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: ZERO),
    )
    for ln in doc.lines:
        key = (ln.account, ln.entity, ln.period)
        groups[key][ln.line_type] += ln.amount

    result: list[IncomeStatementLine] = []
    for (account, entity, period), totals in groups.items():
        budget = totals.get(LineType.BUDGET, ZERO)
        actual = totals.get(LineType.ACTUAL, ZERO)
        forecast = totals.get(LineType.FORECAST, ZERO)
        result.append(
            IncomeStatementLine(
                account=account,
                entity=entity,
                period=period,
                budget=budget,
                actual=actual,
                forecast=forecast,
                variance_bva=actual - budget,
                variance_bvf=forecast - budget,
            ),
        )
    return result


# ---------------------------------------------------------------------------
# Intercompany elimination
# ---------------------------------------------------------------------------


def eliminate_intercompany(
    doc: FinancialDocument,
    elim: EntityCode,
) -> FinancialDocument:
    """Return a new document with lines for the elimination entity removed."""
    return doc.model_copy(
        update={
            "lines": tuple(ln for ln in doc.lines if ln.entity != elim),
        },
    )
