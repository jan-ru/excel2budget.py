---
inclusion: always
---

# Financial Domain Model — Functional Core / OO Shell

This is the canonical domain model for the project. All code (backend and frontend) should align with these types and principles. Python (Pydantic) is the canonical master, TypeScript (Zod) is the frontend consumer.

The full model is defined in #[[file:FinancialDomainModel.md]].

## Key Rules

- All domain types use `frozen=True` — no mutation, ever
- `FinancialDocument` is the fintran IR — every reader produces one, every writer consumes one
- Pure functions in modules, not methods on classes
- `model_copy(update={})` instead of setters — returns new instance

## Core Types Reference

- `AccountCode`, `EntityCode`, `Period` — NewType string wrappers
- `LineType` — budget / actual / forecast
- `AccountType` — asset / liability / equity / revenue / expense
- `DebitCredit` — D / C
- `Account`, `Entity`, `Period` — dimension models
- `FinancialLine` — core line with account, entity, period, amount, line_type
- `BudgetLine`, `ActualLine`, `ForecastLine` — specialised line types
- `IncomeStatementLine`, `BalanceSheetLine`, `CashflowLine` — computed statement lines
- `FinancialDocument` — top-level IR containing lines, accounts, entities, meta
