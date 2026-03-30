/**
 * Property tests for frontend Zod domain schemas.
 *
 * Feature: financial-domain-model
 * Property 5: Zod schema accepts all valid backend-produced FinancialDocument JSON
 * Property 6: Zod validation surfaces descriptive errors for invalid payloads
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  FinancialDocumentSchema,
  FinancialLineSchema,
  AccountSchema,
  EntitySchema,
  BudgetLineSchema,
  ActualLineSchema,
  ForecastLineSchema,
} from "../../src/types/domain";
import {
  financialDocumentArb,
  financialLineArb,
  accountArb,
  entityArb,
  budgetLineArb,
  actualLineArb,
  forecastLineArb,
} from "../arbitraries/domain";

const NUM_RUNS = 100;

// ---------------------------------------------------------------------------
// Property 5: Zod schema accepts all valid backend-produced FinancialDocument JSON
// ---------------------------------------------------------------------------

describe("Property 5: Zod accepts valid backend JSON", () => {
  it("FinancialDocumentSchema parses any valid FinancialDocument", () => {
    fc.assert(
      fc.property(financialDocumentArb, (doc) => {
        const json = JSON.stringify(doc);
        const result = FinancialDocumentSchema.safeParse(JSON.parse(json));
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("FinancialLineSchema parses any valid FinancialLine", () => {
    fc.assert(
      fc.property(financialLineArb, (line) => {
        const result = FinancialLineSchema.safeParse(line);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("AccountSchema parses any valid Account", () => {
    fc.assert(
      fc.property(accountArb, (account) => {
        const result = AccountSchema.safeParse(account);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("EntitySchema parses any valid Entity", () => {
    fc.assert(
      fc.property(entityArb, (entity) => {
        const result = EntitySchema.safeParse(entity);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("BudgetLineSchema parses any valid BudgetLine", () => {
    fc.assert(
      fc.property(budgetLineArb, (line) => {
        const result = BudgetLineSchema.safeParse(line);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("ActualLineSchema parses any valid ActualLine", () => {
    fc.assert(
      fc.property(actualLineArb, (line) => {
        const result = ActualLineSchema.safeParse(line);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("ForecastLineSchema parses any valid ForecastLine", () => {
    fc.assert(
      fc.property(forecastLineArb, (line) => {
        const result = ForecastLineSchema.safeParse(line);
        expect(result.success).toBe(true);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  it("FinancialDocument JSON round-trip through Zod", () => {
    fc.assert(
      fc.property(financialDocumentArb, (doc) => {
        const json = JSON.stringify(doc);
        const parsed = FinancialDocumentSchema.parse(JSON.parse(json));
        // Verify structural equality (ignoring brand symbols)
        expect(parsed.lines.length).toBe(doc.lines.length);
        expect(parsed.accounts.length).toBe(doc.accounts.length);
        expect(parsed.entities.length).toBe(doc.entities.length);
      }),
      { numRuns: NUM_RUNS },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 6: Zod validation surfaces descriptive errors for invalid payloads
// ---------------------------------------------------------------------------

describe("Property 6: Zod error messages are descriptive", () => {
  it("missing required top-level fields produce errors with field path", () => {
    fc.assert(
      fc.property(
        fc.constantFrom("lines", "accounts", "entities", "meta"),
        (field) => {
          // Build a valid-ish doc then remove one required field
          const doc: Record<string, unknown> = {
            lines: [],
            accounts: [],
            entities: [],
            meta: {},
          };
          delete doc[field];

          const result = FinancialDocumentSchema.safeParse(doc);
          expect(result.success).toBe(false);
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join("."));
            expect(paths).toContain(field);
          }
        },
      ),
      { numRuns: NUM_RUNS },
    );
  });

  it("wrong type for lines produces error with expected type", () => {
    const result = FinancialDocumentSchema.safeParse({
      lines: "not-an-array",
      accounts: [],
      entities: [],
      meta: {},
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const linesIssue = result.error.issues.find((i) => i.path[0] === "lines");
      expect(linesIssue).toBeDefined();
      expect(linesIssue!.message).toMatch(/array/i);
    }
  });

  it("invalid line_type in a FinancialLine produces error with path", () => {
    fc.assert(
      fc.property(
        fc.string().filter((s) => !["budget", "actual", "forecast"].includes(s)),
        (badType) => {
          const result = FinancialLineSchema.safeParse({
            account: "4001",
            entity: "MS",
            period: "2025-01",
            amount: "100.00",
            line_type: badType,
          });
          expect(result.success).toBe(false);
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join("."));
            expect(paths).toContain("line_type");
          }
        },
      ),
      { numRuns: NUM_RUNS },
    );
  });

  it("invalid account_type in Account produces error with path", () => {
    fc.assert(
      fc.property(
        fc.string().filter(
          (s) => !["asset", "liability", "equity", "revenue", "expense"].includes(s),
        ),
        (badType) => {
          const result = AccountSchema.safeParse({
            code: "4001",
            description: "Test",
            account_type: badType,
            normal_balance: "D",
          });
          expect(result.success).toBe(false);
          if (!result.success) {
            const paths = result.error.issues.map((i) => i.path.join("."));
            expect(paths).toContain("account_type");
          }
        },
      ),
      { numRuns: NUM_RUNS },
    );
  });

  it("non-string amount in FinancialLine produces error", () => {
    const result = FinancialLineSchema.safeParse({
      account: "4001",
      entity: "MS",
      period: "2025-01",
      amount: 12345,
      line_type: "budget",
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      const amountIssue = result.error.issues.find((i) => i.path[0] === "amount");
      expect(amountIssue).toBeDefined();
      expect(amountIssue!.message).toMatch(/string/i);
    }
  });
});
