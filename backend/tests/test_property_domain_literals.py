# Feature: financial-domain-model, Property 2: Specialised line type Literal constraint
# Validates: Requirements 1.5
"""Property test: specialised lines lock line_type; mismatched construction raises ValidationError."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from pydantic import ValidationError

from backend.app.core.domain import ActualLine, BudgetLine, ForecastLine, LineType
from backend.tests.strategies import actual_lines, budget_lines, forecast_lines


@settings(max_examples=100)
@given(line=budget_lines)
def test_budget_line_type_is_budget(line: BudgetLine) -> None:
    assert line.line_type == LineType.BUDGET
    assert line.line_type == "budget"


@settings(max_examples=100)
@given(line=actual_lines)
def test_actual_line_type_is_actual(line: ActualLine) -> None:
    assert line.line_type == LineType.ACTUAL
    assert line.line_type == "actual"


@settings(max_examples=100)
@given(line=forecast_lines)
def test_forecast_line_type_is_forecast(line: ForecastLine) -> None:
    assert line.line_type == LineType.FORECAST
    assert line.line_type == "forecast"


def test_budget_line_rejects_mismatched_line_type() -> None:
    with pytest.raises(ValidationError):
        BudgetLine(
            account="4001",
            entity="MS",
            period="2025-01",
            amount=100,
            line_type="actual",  # type: ignore[arg-type]
        )


def test_actual_line_rejects_mismatched_line_type() -> None:
    with pytest.raises(ValidationError):
        ActualLine(
            account="4001",
            entity="MS",
            period="2025-01",
            amount=100,
            line_type="budget",  # type: ignore[arg-type]
        )


def test_forecast_line_rejects_mismatched_line_type() -> None:
    with pytest.raises(ValidationError):
        ForecastLine(
            account="4001",
            entity="MS",
            period="2025-01",
            amount=100,
            line_type="budget",  # type: ignore[arg-type]
        )
