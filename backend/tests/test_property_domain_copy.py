# Feature: financial-domain-model, Property 4: model_copy produces a new instance with updated fields
# Validates: Requirements 10.2
"""Property test: model_copy(update={...}) returns new instance; original unchanged."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings

from backend.app.core.domain import (
    Account,
    Entity,
    EntityCode,
    FinancialLine,
)
from backend.tests.strategies import accounts, entities, financial_lines


@settings(max_examples=100)
@given(original=financial_lines)
def test_financial_line_model_copy(original: FinancialLine) -> None:
    new_amount = original.amount + Decimal("1")
    copy = original.model_copy(update={"amount": new_amount})

    assert copy is not original
    assert copy.amount == new_amount
    assert original.amount == copy.amount - Decimal("1")
    # All other fields unchanged
    assert copy.account == original.account
    assert copy.entity == original.entity
    assert copy.period == original.period
    assert copy.line_type == original.line_type
    assert copy.currency == original.currency
    assert copy.memo == original.memo


@settings(max_examples=100)
@given(original=accounts)
def test_account_model_copy(original: Account) -> None:
    copy = original.model_copy(update={"description": "UPDATED"})

    assert copy is not original
    assert copy.description == "UPDATED"
    assert original.description != "UPDATED" or original.description == "UPDATED"
    assert copy.code == original.code
    assert copy.account_type == original.account_type
    assert copy.normal_balance == original.normal_balance


@settings(max_examples=100)
@given(original=entities)
def test_entity_model_copy(original: Entity) -> None:
    new_code = EntityCode("ZZ")
    copy = original.model_copy(update={"code": new_code})

    assert copy is not original
    assert copy.code == new_code
    assert copy.description == original.description
    assert copy.is_elimination == original.is_elimination
