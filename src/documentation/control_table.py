"""Control Table Generator for the Documentation Module.

Generates a reconciliation sheet proving input totals equal output totals.

Requirements: 17.6.1, 17.6.2, 17.6.3, 17.6.4, 17.6.5
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.types import (
    ApplicationContext,
    ControlTable,
)


def generate_control_table(context: ApplicationContext) -> ControlTable:
    """Generate a ControlTable from the ApplicationContext.

    The control totals are pre-computed by the application module
    (e.g., excel2budget) and stored in context.controlTotals.
    This generator wraps them with a generation timestamp.

    Args:
        context: The generic ApplicationContext with controlTotals populated.

    Returns:
        A ControlTable with the totals and a generatedAt timestamp.
    """
    if context.controlTotals is None:
        from src.core.types import ControlTotals
        totals = ControlTotals()
    else:
        totals = context.controlTotals

    return ControlTable(
        totals=totals,
        generatedAt=datetime.now(timezone.utc),
    )
