/**
 * Reusable fast-check arbitraries mirroring backend Hypothesis strategies.
 */

import fc from "fast-check";

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

export const accountCodeArb = fc.stringMatching(/^[0-9]{4}$/);
export const entityCodeArb = fc.constantFrom("MS", "MH", "EL", "IC");
export const periodArb = fc.stringMatching(/^20[2-3][0-9]-(0[1-9]|1[0-2])$/);
export const amountArb = fc
  .double({ min: -1_000_000, max: 1_000_000, noNaN: true, noDefaultInfinity: true })
  .map((v) => v.toFixed(4));

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export const lineTypeArb = fc.constantFrom("budget", "actual", "forecast");
export const accountTypeArb = fc.constantFrom("asset", "liability", "equity", "revenue", "expense");
export const debitCreditArb = fc.constantFrom("D", "C");

// ---------------------------------------------------------------------------
// Dimension models
// ---------------------------------------------------------------------------

export const accountArb = fc.record({
  code: accountCodeArb,
  description: fc.string({ minLength: 1, maxLength: 40 }),
  account_type: accountTypeArb,
  normal_balance: debitCreditArb,
  parent_code: fc.option(accountCodeArb, { nil: null }),
});

export const entityArb = fc.record({
  code: entityCodeArb,
  description: fc.string({ minLength: 1, maxLength: 40 }),
  is_elimination: fc.boolean(),
});

// ---------------------------------------------------------------------------
// Line types
// ---------------------------------------------------------------------------

export const financialLineArb = fc.record({
  account: accountCodeArb,
  entity: entityCodeArb,
  period: periodArb,
  amount: amountArb,
  line_type: lineTypeArb,
  currency: fc.constant("EUR"),
  memo: fc.option(fc.string({ maxLength: 30 }), { nil: null }),
});

export const budgetLineArb = fc.record({
  account: accountCodeArb,
  entity: entityCodeArb,
  period: periodArb,
  amount: amountArb,
  line_type: fc.constant("budget" as const),
  currency: fc.constant("EUR"),
  memo: fc.option(fc.string({ maxLength: 30 }), { nil: null }),
  version: fc.constant("v1"),
});

export const actualLineArb = fc.record({
  account: accountCodeArb,
  entity: entityCodeArb,
  period: periodArb,
  amount: amountArb,
  line_type: fc.constant("actual" as const),
  currency: fc.constant("EUR"),
  memo: fc.option(fc.string({ maxLength: 30 }), { nil: null }),
  journal_ref: fc.option(fc.string({ maxLength: 20 }), { nil: null }),
});

export const forecastLineArb = fc.record({
  account: accountCodeArb,
  entity: entityCodeArb,
  period: periodArb,
  amount: amountArb,
  line_type: fc.constant("forecast" as const),
  currency: fc.constant("EUR"),
  memo: fc.option(fc.string({ maxLength: 30 }), { nil: null }),
  basis: fc.constantFrom("manual", "actuals_adjusted", "budget_adjusted"),
});

// ---------------------------------------------------------------------------
// FinancialDocument
// ---------------------------------------------------------------------------

export const financialDocumentArb = fc.record({
  lines: fc.array(financialLineArb, { maxLength: 50 }),
  accounts: fc.array(accountArb, { maxLength: 10 }),
  entities: fc.array(entityArb, { maxLength: 5 }),
  meta: fc.dictionary(
    fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s.trim().length > 0),
    fc.string({ maxLength: 100 }),
    { maxKeys: 5 },
  ),
});
