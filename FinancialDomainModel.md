# Financial Domain Model — Functional Core / OO Shell

Python (Pydantic) as canonical master, TypeScript (Zod) as frontend consumer.

## Primitive Types

```python
from pydantic import BaseModel
from decimal import Decimal
from typing import Literal, NewType
from enum import StrEnum

AccountCode = NewType("AccountCode", str)   # e.g. "4001"
EntityCode  = NewType("EntityCode", str)    # e.g. "MS", "MH", "EL"
Period      = NewType("Period", str)        # e.g. "2025-03"


class LineType(StrEnum):
    BUDGET   = "budget"
    ACTUAL   = "actual"
    FORECAST = "forecast"


class AccountType(StrEnum):
    ASSET     = "asset"
    LIABILITY = "liability"
    EQUITY    = "equity"
    REVENUE   = "revenue"
    EXPENSE   = "expense"


class DebitCredit(StrEnum):
    DEBIT  = "D"
    CREDIT = "C"
```

## Dimension Models

```python
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


class Period(BaseModel, frozen=True):
    value: str        # "2025-03"
    year: int
    month: int
    fiscal_year: int
```

## Core Financial Line

```python
class FinancialLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    amount: Decimal
    line_type: LineType
    currency: str = "EUR"
    memo: str | None = None
```

## Specialised Line Types

```python
class BudgetLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.BUDGET] = LineType.BUDGET
    version: str = "v1"


class ActualLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.ACTUAL] = LineType.ACTUAL
    journal_ref: str | None = None


class ForecastLine(FinancialLine, frozen=True):
    line_type: Literal[LineType.FORECAST] = LineType.FORECAST
    basis: Literal["manual", "actuals_adjusted", "budget_adjusted"] = "manual"
```

## Statement Lines (computed, never stored)

```python
class IncomeStatementLine(BaseModel, frozen=True):
    account: AccountCode
    entity: EntityCode
    period: str
    budget: Decimal
    actual: Decimal
    forecast: Decimal
    variance_bva: Decimal   # actual vs budget
    variance_bvf: Decimal   # forecast vs budget


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
```

## Intermediate Representation (fintran IR)

```python
class FinancialDocument(BaseModel, frozen=True):
    """Top-level IR — output of any reader, input to any writer."""
    lines: tuple[FinancialLine, ...]
    accounts: tuple[Account, ...]
    entities: tuple[Entity, ...]
    meta: dict[str, str]
```

## Pure Function Layer (signatures)

```python
def filter_entity(doc: FinancialDocument, entity: EntityCode) -> FinancialDocument: ...
def filter_period(doc: FinancialDocument, year: int) -> FinancialDocument: ...
def to_polars(doc: FinancialDocument) -> pl.DataFrame: ...
def from_polars(df: pl.DataFrame) -> FinancialDocument: ...
def compute_variance(doc: FinancialDocument) -> list[IncomeStatementLine]: ...
def eliminate_intercompany(doc: FinancialDocument, elim: EntityCode) -> FinancialDocument: ...
```

## Design Principles

- `frozen=True` on all models — no mutation, ever
- `model_copy(update={})` instead of setters — returns new instance
- Pure functions in modules, not methods on the class
- Polars as the bulk engine — convert Pydantic models to/from DataFrames at boundaries only
- `FinancialDocument` is the fintran IR — every reader produces one, every writer consumes one
