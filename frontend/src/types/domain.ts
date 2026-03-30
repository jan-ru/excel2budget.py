/**
 * Financial Domain Model — Zod schemas mirroring backend Pydantic models.
 *
 * Canonical reference: FinancialDomainModel.md
 * Backend source of truth: backend/app/core/domain.py
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Primitive types (branded strings)
// ---------------------------------------------------------------------------

export const AccountCodeSchema = z.string().brand<"AccountCode">();
export const EntityCodeSchema = z.string().brand<"EntityCode">();

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export const LineTypeSchema = z.enum(["budget", "actual", "forecast"]);
export const AccountTypeSchema = z.enum(["asset", "liability", "equity", "revenue", "expense"]);
export const DebitCreditSchema = z.enum(["D", "C"]);

// ---------------------------------------------------------------------------
// Dimension models
// ---------------------------------------------------------------------------

export const AccountSchema = z
  .object({
    code: AccountCodeSchema,
    description: z.string(),
    account_type: AccountTypeSchema,
    normal_balance: DebitCreditSchema,
    parent_code: AccountCodeSchema.nullable().default(null),
  })
  .readonly();

export const EntitySchema = z
  .object({
    code: EntityCodeSchema,
    description: z.string(),
    is_elimination: z.boolean().default(false),
  })
  .readonly();

// ---------------------------------------------------------------------------
// Core financial line
// ---------------------------------------------------------------------------

const financialLineShape = {
  account: AccountCodeSchema,
  entity: EntityCodeSchema,
  period: z.string(),
  amount: z.string(), // Decimal serialised as string for precision
  line_type: LineTypeSchema,
  currency: z.string().default("EUR"),
  memo: z.string().nullable().default(null),
};

export const FinancialLineSchema = z.object(financialLineShape).readonly();

// ---------------------------------------------------------------------------
// Specialised line types
// ---------------------------------------------------------------------------

export const BudgetLineSchema = z
  .object({
    ...financialLineShape,
    line_type: z.literal("budget"),
    version: z.string().default("v1"),
  })
  .readonly();

export const ActualLineSchema = z
  .object({
    ...financialLineShape,
    line_type: z.literal("actual"),
    journal_ref: z.string().nullable().default(null),
  })
  .readonly();

export const ForecastLineSchema = z
  .object({
    ...financialLineShape,
    line_type: z.literal("forecast"),
    basis: z.enum(["manual", "actuals_adjusted", "budget_adjusted"]).default("manual"),
  })
  .readonly();

// ---------------------------------------------------------------------------
// Statement lines (computed, never stored)
// ---------------------------------------------------------------------------

export const IncomeStatementLineSchema = z
  .object({
    account: AccountCodeSchema,
    entity: EntityCodeSchema,
    period: z.string(),
    budget: z.string(),
    actual: z.string(),
    forecast: z.string(),
    variance_bva: z.string(),
    variance_bvf: z.string(),
  })
  .readonly();

export const BalanceSheetLineSchema = z
  .object({
    account: AccountCodeSchema,
    entity: EntityCodeSchema,
    period: z.string(),
    balance: z.string(),
    line_type: LineTypeSchema,
  })
  .readonly();

export const CashflowLineSchema = z
  .object({
    account: AccountCodeSchema,
    entity: EntityCodeSchema,
    period: z.string(),
    inflow: z.string(),
    outflow: z.string(),
    net: z.string(),
    line_type: LineTypeSchema,
  })
  .readonly();

// ---------------------------------------------------------------------------
// Top-level IR
// ---------------------------------------------------------------------------

export const FinancialDocumentSchema = z
  .object({
    lines: z.array(FinancialLineSchema).readonly(),
    accounts: z.array(AccountSchema).readonly(),
    entities: z.array(EntitySchema).readonly(),
    meta: z.record(z.string(), z.string()),
  })
  .readonly();

// ---------------------------------------------------------------------------
// Inferred TypeScript types
// ---------------------------------------------------------------------------

export type AccountCode = z.infer<typeof AccountCodeSchema>;
export type EntityCode = z.infer<typeof EntityCodeSchema>;
export type LineType = z.infer<typeof LineTypeSchema>;
export type AccountType = z.infer<typeof AccountTypeSchema>;
export type DebitCredit = z.infer<typeof DebitCreditSchema>;
export type Account = z.infer<typeof AccountSchema>;
export type Entity = z.infer<typeof EntitySchema>;
export type FinancialLine = z.infer<typeof FinancialLineSchema>;
export type BudgetLine = z.infer<typeof BudgetLineSchema>;
export type ActualLine = z.infer<typeof ActualLineSchema>;
export type ForecastLine = z.infer<typeof ForecastLineSchema>;
export type IncomeStatementLine = z.infer<typeof IncomeStatementLineSchema>;
export type BalanceSheetLine = z.infer<typeof BalanceSheetLineSchema>;
export type CashflowLine = z.infer<typeof CashflowLineSchema>;
export type FinancialDocument = z.infer<typeof FinancialDocumentSchema>;
