"""Control Table Generator for the Documentation Module.

Generates a reconciliation sheet proving input totals equal output totals.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.types import (
    ApplicationContext,
    ControlTable,
    ControlTotals,
)


def generate_control_table(context: ApplicationContext) -> ControlTable:
    """Generate a ControlTable from the ApplicationContext.

    The control totals are pre-computed by the application module
    and stored in context.controlTotals. This generator wraps them
    with a generation timestamp.
    """
    totals = (
        context.controlTotals if context.controlTotals is not None else ControlTotals()
    )

    return ControlTable(
        totals=totals,
        generatedAt=datetime.now(timezone.utc),
    )
