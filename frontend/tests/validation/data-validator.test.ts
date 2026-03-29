import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  validateMappingConfig,
  validateUserParams,
  validateDCValues,
} from "../../src/validation/data-validator";
import type { components } from "../../src/types/api";

type MappingConfig = components["schemas"]["MappingConfig"];
type MonthColumnDef = components["schemas"]["MonthColumnDef"];
type TabularData = components["schemas"]["TabularData"];
type Row = components["schemas"]["Row"];
type CellValue = Row["values"][number];

// --- Arbitraries ---

/** Generate a valid column name (non-empty, no duplicates handled by caller). */
const arbColName = fc.stringOf(fc.char().filter((c) => c.trim() === c && c !== ""), {
  minLength: 1,
  maxLength: 20,
});

/** Generate a valid MonthColumnDef with period in 1–12. */
function arbMonthCol(sourceColumnName: string, periodNumber: number): fc.Arbitrary<MonthColumnDef> {
  return fc.record({
    sourceColumnName: fc.constant(sourceColumnName),
    periodNumber: fc.constant(periodNumber),
    year: fc.integer({ min: 2000, max: 2099 }),
  });
}

// ---------------------------------------------------------------------------
// Property 9: MappingConfig Validation
// ---------------------------------------------------------------------------

describe("Property 9: MappingConfig Validation", () => {
  it("reports error when referenced columns are missing from column list", () => {
    fc.assert(
      fc.property(
        arbColName,
        arbColName,
        arbColName,
        arbColName,
        (entity, account, dc, monthSrc) => {
          // Ensure all names are distinct
          const names = [entity, account, dc, monthSrc];
          if (new Set(names).size !== names.length) return; // skip collisions

          const config: MappingConfig = {
            entityColumn: entity,
            accountColumn: account,
            dcColumn: dc,
            monthColumns: [{ sourceColumnName: monthSrc, periodNumber: 1, year: 2026 }],
          };

          // Provide an empty column list — all references should be missing
          const result = validateMappingConfig(config, []);
          expect(result.valid).toBe(false);
          expect(result.errors.length).toBeGreaterThanOrEqual(4);
          expect(result.errors.some((e) => e.includes(entity))).toBe(true);
          expect(result.errors.some((e) => e.includes(account))).toBe(true);
          expect(result.errors.some((e) => e.includes(dc))).toBe(true);
          expect(result.errors.some((e) => e.includes(monthSrc))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports error for period numbers outside 1–12", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 13, max: 1000 }),
        (badPeriod) => {
          const colNames = ["Entity", "Account", "DC", "month-col"];
          const config: MappingConfig = {
            entityColumn: "Entity",
            accountColumn: "Account",
            dcColumn: "DC",
            monthColumns: [
              { sourceColumnName: "month-col", periodNumber: badPeriod, year: 2026 },
            ],
          };

          const result = validateMappingConfig(config, colNames);
          expect(result.valid).toBe(false);
          expect(result.errors.some((e) => e.includes("out of range"))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports error for negative/zero period numbers", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: -100, max: 0 }),
        (badPeriod) => {
          const colNames = ["Entity", "Account", "DC", "month-col"];
          const config: MappingConfig = {
            entityColumn: "Entity",
            accountColumn: "Account",
            dcColumn: "DC",
            monthColumns: [
              { sourceColumnName: "month-col", periodNumber: badPeriod, year: 2026 },
            ],
          };

          const result = validateMappingConfig(config, colNames);
          expect(result.valid).toBe(false);
          expect(result.errors.some((e) => e.includes("out of range"))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports error for duplicate period numbers", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 12 }),
        (period) => {
          const colNames = ["Entity", "Account", "DC", "m1", "m2"];
          const config: MappingConfig = {
            entityColumn: "Entity",
            accountColumn: "Account",
            dcColumn: "DC",
            monthColumns: [
              { sourceColumnName: "m1", periodNumber: period, year: 2026 },
              { sourceColumnName: "m2", periodNumber: period, year: 2026 },
            ],
          };

          const result = validateMappingConfig(config, colNames);
          expect(result.valid).toBe(false);
          expect(result.errors.some((e) => e.includes("Duplicate periodNumber"))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("accepts valid MappingConfig with all columns present and unique periods", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 12 }),
        (numMonths) => {
          const colNames = ["Entity", "Account", "DC"];
          const monthCols: MonthColumnDef[] = [];
          for (let i = 1; i <= numMonths; i++) {
            const name = `m${i}`;
            colNames.push(name);
            monthCols.push({ sourceColumnName: name, periodNumber: i, year: 2026 });
          }

          const config: MappingConfig = {
            entityColumn: "Entity",
            accountColumn: "Account",
            dcColumn: "DC",
            monthColumns: monthCols,
          };

          const result = validateMappingConfig(config, colNames);
          expect(result.valid).toBe(true);
          expect(result.errors).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 10: UserParams Validation
// ---------------------------------------------------------------------------

describe("Property 10: UserParams Validation", () => {
  it("reports failure for empty budgetcode", () => {
    fc.assert(
      fc.property(
        fc.constantFrom("", " ", "  ", "\t", "\n"),
        fc.integer({ min: 1, max: 9999 }),
        (budgetcode, year) => {
          const result = validateUserParams({ budgetcode, year });
          expect(result.valid).toBe(false);
          expect(result.errors.some((e) => e.includes("budgetcode"))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports failure for non-positive year", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: -9999, max: 0 }),
        (year) => {
          const result = validateUserParams({ budgetcode: "ABC", year });
          expect(result.valid).toBe(false);
          expect(result.errors.some((e) => e.includes("year"))).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports both errors when budgetcode is empty AND year is non-positive", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: -9999, max: 0 }),
        (year) => {
          const result = validateUserParams({ budgetcode: "", year });
          expect(result.valid).toBe(false);
          expect(result.errors.length).toBe(2);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("accepts valid UserParams", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
        fc.integer({ min: 1, max: 9999 }),
        (budgetcode, year) => {
          const result = validateUserParams({ budgetcode, year });
          expect(result.valid).toBe(true);
          expect(result.errors).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Property 11: DC Value Validation
// ---------------------------------------------------------------------------

describe("Property 11: DC Value Validation", () => {
  /** Build a minimal TabularData with a DC column and the given cell values. */
  function buildDCData(dcValues: CellValue[]): TabularData {
    const rows: Row[] = dcValues.map((v) => ({ values: [v] }));
    return {
      columns: [{ name: "DC", dataType: "STRING", nullable: true }],
      rows,
      rowCount: rows.length,
      metadata: {
        sourceName: "",
        sourceFormat: "EXCEL",
        importedAt: null,
        transformedAt: null,
        exportedAt: null,
        encoding: "utf-8",
      },
    };
  }

  it("detects every row with an invalid DC value, including row index and value", () => {
    // Generate a mix of valid and invalid DC values
    const validDC: fc.Arbitrary<CellValue> = fc.constantFrom(
      { type: "string" as const, value: "D" },
      { type: "string" as const, value: "C" },
      { type: "null" as const },
    );

    const invalidDC: fc.Arbitrary<CellValue> = fc.oneof(
      fc.string({ minLength: 1, maxLength: 10 })
        .filter((s) => s !== "D" && s !== "C")
        .map((s): CellValue => ({ type: "string", value: s })),
      fc.integer().map((n): CellValue => ({ type: "int", value: n })),
      fc.float().map((n): CellValue => ({ type: "float", value: n })),
      fc.boolean().map((b): CellValue => ({ type: "bool", value: b })),
    );

    fc.assert(
      fc.property(
        fc.array(fc.oneof(validDC, invalidDC), { minLength: 1, maxLength: 50 }),
        (dcValues) => {
          const data = buildDCData(dcValues);
          const result = validateDCValues(data, "DC");

          // Compute expected invalid row indices
          const expectedInvalid: number[] = [];
          for (let i = 0; i < dcValues.length; i++) {
            const v = dcValues[i];
            const isValid =
              v.type === "null" ||
              (v.type === "string" && (v.value === "D" || v.value === "C"));
            if (!isValid) expectedInvalid.push(i);
          }

          expect(result.errors.length).toBe(expectedInvalid.length);
          expect(result.valid).toBe(expectedInvalid.length === 0);

          // Each invalid row should be reported with its index
          for (const idx of expectedInvalid) {
            expect(result.errors.some((e) => e.includes(`Row ${idx}`))).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("accepts data where all DC values are valid (D, C, or null)", () => {
    const validDC: fc.Arbitrary<CellValue> = fc.constantFrom(
      { type: "string" as const, value: "D" },
      { type: "string" as const, value: "C" },
      { type: "null" as const },
    );

    fc.assert(
      fc.property(
        fc.array(validDC, { minLength: 0, maxLength: 50 }),
        (dcValues) => {
          const data = buildDCData(dcValues);
          const result = validateDCValues(data, "DC");
          expect(result.valid).toBe(true);
          expect(result.errors).toEqual([]);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("reports error when DC column is not found", () => {
    const data: TabularData = {
      columns: [{ name: "Other", dataType: "STRING", nullable: true }],
      rows: [],
      rowCount: 0,
      metadata: {
        sourceName: "",
        sourceFormat: "EXCEL",
        importedAt: null,
        transformedAt: null,
        exportedAt: null,
        encoding: "utf-8",
      },
    };

    const result = validateDCValues(data, "DC");
    expect(result.valid).toBe(false);
    expect(result.errors[0]).toContain("DC column 'DC' not found");
  });
});
