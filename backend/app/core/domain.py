"""Financial Domain Model — immutable Pydantic types.

Canonical reference: FinancialDomainModel.md

All models use ``frozen=True`` — no mutation, ever.
``model_copy(update={})`` instead of setters — returns new instance.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal, NewType

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Primitive types
# ---------------------------------------------------------------------------

AccountCode = NewType("AccountCode", str)
EntityCode = NewType("EntityCode", str)
Period = NewType("Period", str)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LineType(StrEnum):
    BUDGET = "budget"
    ACTUAL = "actual"
    FORECAST = "forecast"


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class DebitCredit(StrEnum):
    DEBIT = "D"
    CREDIT = "C"


# ---------------------------------------------------------------------------
# Dimension models
# ---------------------------------------------------------------------------


class Account(BaseModel, frozen=True):
    code: AccountCode
    description: str
    account_type: AccountType
    normal_balance: DebitCredit
    parent_code: AccountCode | None = None


class Entity(BaseModel, frozen=True):
    code: EntityCode
    description: str
    is_elimination: bool = False


class Period(BaseModel, frozen=True):  # noqa: F811 — shadows NewType on purpose
    value: str
    year: int
    month: int
    fiscal_year: int


# ---------------------------------------------------------------------------
# Core financial line
# ---------------------------------------------------------------------------


class FinancialLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    amount: Decimal
    line_type: LineType
    currency: str = "EUR"
    memo: str | None = None


# ---------------------------------------------------------------------------
# Specialised line types
# ---------------------------------------------------------------------------


class BudgetLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.BUDGET] = LineType.BUDGET
    version: str = "v1"


class ActualLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.ACTUAL] = LineType.ACTUAL
    journal_ref: str | None = None


class ForecastLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.FORECAST] = LineType.FORECAST
    basis: Literal["manual", "actuals_adjusted", "budget_adjusted"] = "manual"


# ---------------------------------------------------------------------------
# Statement lines (computed, never stored)
# ---------------------------------------------------------------------------


class IncomeStatementLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    budget: Decimal
    actual: Decimal
    forecast: Decimal
    variance_bva: Decimal
    variance_bvf: Decimal


class BalanceSheetLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    balance: Decimal
    line_type: LineType


class CashflowLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    inflow: Decimal
    outflow: Decimal
    net: Decimal
    line_type: LineType


# ---------------------------------------------------------------------------
# Top-level IR
# ---------------------------------------------------------------------------


class FinancialDocument(BaseModel, frozen=True):
    """Top-level IR — output of any reader, input to any writer."""

    lines: tuple[FinancialLine, ...]
    accounts: tuple[Account, ...]
    entities: tuple[Entity, ...]
    meta: dict[str, str]
