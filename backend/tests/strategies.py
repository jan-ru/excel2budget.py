"""Reusable Hypothesis strategies for the Financial Domain Model.

Used by all property-based tests in the backend test suite.
"""

from __future__ import annotations

from hypothesis import strategies as st

from backend.app.core.domain import (
    Account,
    AccountCode,
    AccountType,
    ActualLine,
    BalanceSheetLine,
    BudgetLine,
    CashflowLine,
    DebitCredit,
    Entity,
    EntityCode,
    FinancialDocument,
    FinancialLine,
    ForecastLine,
    IncomeStatementLine,
    LineType,
)

# ---------------------------------------------------------------------------
# Primitive strategies
# ---------------------------------------------------------------------------

account_codes = st.from_regex(r"[0-9]{4}", fullmatch=True).map(AccountCode)
entity_codes = st.sampled_from(["MS", "MH", "EL", "IC"]).map(EntityCode)
periods = st.from_regex(r"20[2-3][0-9]-(0[1-9]|1[0-2])", fullmatch=True)
amounts = st.decimals(
    min_value=-1_000_000,
    max_value=1_000_000,
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# ---------------------------------------------------------------------------
# Dimension model strategies
# ---------------------------------------------------------------------------

accounts = st.builds(
    Account,
    code=account_codes,
    description=st.text(min_size=1, max_size=50),
    account_type=st.sampled_from(AccountType),
    normal_balance=st.sampled_from(DebitCredit),
    parent_code=st.none() | account_codes,
)

entities = st.builds(
    Entity,
    code=entity_codes,
    description=st.text(min_size=1, max_size=50),
    is_elimination=st.booleans(),
)

# ---------------------------------------------------------------------------
# Line strategies
# ---------------------------------------------------------------------------

financial_lines = st.builds(
    FinancialLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    amount=amounts,
    line_type=st.sampled_from(LineType),
    currency=st.just("EUR"),
    memo=st.none() | st.text(max_size=30),
)

budget_lines = st.builds(
    BudgetLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    amount=amounts,
    version=st.just("v1"),
)

actual_lines = st.builds(
    ActualLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    amount=amounts,
    journal_ref=st.none() | st.text(max_size=20),
)

forecast_lines = st.builds(
    ForecastLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    amount=amounts,
    basis=st.sampled_from(["manual", "actuals_adjusted", "budget_adjusted"]),
)

# ---------------------------------------------------------------------------
# Statement line strategies
# ---------------------------------------------------------------------------

income_statement_lines = st.builds(
    IncomeStatementLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    budget=amounts,
    actual=amounts,
    forecast=amounts,
    variance_bva=amounts,
    variance_bvf=amounts,
)

balance_sheet_lines = st.builds(
    BalanceSheetLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    balance=amounts,
    line_type=st.sampled_from(LineType),
)

cashflow_lines = st.builds(
    CashflowLine,
    account=account_codes,
    entity=entity_codes,
    period=periods,
    inflow=amounts,
    outflow=amounts,
    net=amounts,
    line_type=st.sampled_from(LineType),
)

# ---------------------------------------------------------------------------
# Top-level IR strategy
# ---------------------------------------------------------------------------

financial_documents = st.builds(
    FinancialDocument,
    lines=st.lists(financial_lines, max_size=50).map(tuple),
    accounts=st.lists(accounts, max_size=10).map(tuple),
    entities=st.lists(entities, max_size=5).map(tuple),
    meta=st.dictionaries(st.text(max_size=20), st.text(max_size=100), max_size=5),
)
