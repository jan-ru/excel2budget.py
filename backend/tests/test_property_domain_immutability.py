# Feature: financial-domain-model, Property 1: Immutability enforcement across all domain models
# Validates: Requirements 1.3, 1.6, 1.8, 10.1
"""Property test: assigning to any field on a frozen domain model raises ValidationError."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from pydantic import ValidationError

from backend.app.core.domain import (
    Account,
    ActualLine,
    BalanceSheetLine,
    BudgetLine,
    CashflowLine,
    Entity,
    FinancialDocument,
    FinancialLine,
    ForecastLine,
    IncomeStatementLine,
    Period,
)
from backend.tests.strategies import (
    accounts,
    actual_lines,
    balance_sheet_lines,
    budget_lines,
    cashflow_lines,
    entities,
    financial_documents,
    financial_lines,
    forecast_lines,
    income_statement_lines,
)


@settings(max_examples=100)
@given(instance=accounts)
def test_account_is_immutable(instance: Account) -> None:
    with pytest.raises(ValidationError):
        instance.code = "9999"  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=entities)
def test_entity_is_immutable(instance: Entity) -> None:
    with pytest.raises(ValidationError):
        instance.code = "XX"  # type: ignore[misc]


@settings(max_examples=100)
@given(
    instance=financial_lines,
)
def test_financial_line_is_immutable(instance: FinancialLine) -> None:
    with pytest.raises(ValidationError):
        instance.amount = instance.amount + 1  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=budget_lines)
def test_budget_line_is_immutable(instance: BudgetLine) -> None:
    with pytest.raises(ValidationError):
        instance.version = "v2"  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=actual_lines)
def test_actual_line_is_immutable(instance: ActualLine) -> None:
    with pytest.raises(ValidationError):
        instance.journal_ref = "changed"  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=forecast_lines)
def test_forecast_line_is_immutable(instance: ForecastLine) -> None:
    with pytest.raises(ValidationError):
        instance.basis = "manual"  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=income_statement_lines)
def test_income_statement_line_is_immutable(instance: IncomeStatementLine) -> None:
    with pytest.raises(ValidationError):
        instance.budget = instance.budget + 1  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=balance_sheet_lines)
def test_balance_sheet_line_is_immutable(instance: BalanceSheetLine) -> None:
    with pytest.raises(ValidationError):
        instance.balance = instance.balance + 1  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=cashflow_lines)
def test_cashflow_line_is_immutable(instance: CashflowLine) -> None:
    with pytest.raises(ValidationError):
        instance.net = instance.net + 1  # type: ignore[misc]


@settings(max_examples=100)
@given(instance=financial_documents)
def test_financial_document_is_immutable(instance: FinancialDocument) -> None:
    with pytest.raises(ValidationError):
        instance.meta = {}  # type: ignore[misc]


def test_period_is_immutable() -> None:
    p = Period(value="2025-03", year=2025, month=3, fiscal_year=2025)
    with pytest.raises(ValidationError):
        p.year = 2026  # type: ignore[misc]
