// Feature: header-row-selection, Property 6: Backward compatibility — full auto-import
/**
 * Property 6: Backward compatibility — full auto-import
 *
 * For any workbook containing a "Budget" sheet with Required_Columns in row 0
 * (plus valid month columns and at least one data row), calling `importFile`
 * SHALL return a successful `Result<TabularData>` without returning
 * `SheetSelectionNeeded` or `HeaderSelectionNeeded`.
 *
 * **Validates: Requirements 1.2, 6.1**
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  PipelineOrchestrator,
  isSheetSelectionNeeded,
  isHeaderSelectionNeeded,
} from "../../src/pipeline/orchestrator";

// --- Helpers ---

/** Characters safe for Excel sheet names (no :\/?*[]') */
const SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-";

/** Arbitrary for a valid Excel sheet name that is NOT "Budget". */
const nonBudgetSheetName = fc
  .stringOf(fc.constantFrom(...SAFE_CHARS), { minLength: 1, maxLength: 20 })
  .map((s) => s.trim())
  .filter((s) => s.length > 0 && s !== "Budget");

/** Arbitrary that produces a random case variation of a string. */
const randomCase = (s: string) =>
  fc
    .array(fc.boolean(), { minLength: s.length, maxLength: s.length })
    .map((flags) =>
      s
        .split("")
        .map((ch, i) => (flags[i] ? ch.toUpperCase() : ch.toLowerCase()))
        .join(""),
    );

/** Dutch month abbreviations matching the importer's MONTH_COLUMN_PATTERN. */
const DUTCH_MONTHS = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];

/** Arbitrary for a valid month column header like "jan-26". */
const monthColumnArb = fc
  .tuple(
    fc.constantFrom(...DUTCH_MONTHS),
    fc.integer({ min: 20, max: 30 }),
  )
  .map(([month, year]) => `${month}-${year}`);

/** Arbitrary for a header row with required columns in random case plus at least one month column. */
const headerRowArb = fc
  .tuple(
    randomCase("Entity"),
    randomCase("Account"),
    randomCase("DC"),
    fc.array(monthColumnArb, { minLength: 1, maxLength: 3 }),
  )
  .map(([entity, account, dc, months]) => [entity, account, dc, ...months]);

/** Arbitrary for a data row matching the column count of the header. */
const dataRowArb = (colCount: number) =>
  fc.array(
    fc.oneof(
      fc.string({ minLength: 1, maxLength: 10 }).filter((s) => s.trim().length > 0),
      fc.integer({ min: 0, max: 9999 }),
    ),
    { minLength: colCount, maxLength: colCount },
  );

/**
 * Build a workbook with a "Budget" sheet that has headers in row 0,
 * valid month columns, and at least one data row.
 * Optionally includes extra non-Budget sheets.
 */
function buildBackwardCompatWorkbook(
  headerRow: unknown[],
  dataRows: unknown[][],
  extraSheetNames: string[],
): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  // Budget sheet: header in row 0 + data rows
  const budgetData = [headerRow, ...dataRows];
  const budgetWs = XLSX.utils.aoa_to_sheet(budgetData);
  XLSX.utils.book_append_sheet(wb, budgetWs, "Budget");

  // Extra sheets with minimal content
  for (const name of extraSheetNames) {
    const ws = XLSX.utils.aoa_to_sheet([["col1"], ["val1"]]);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }

  return wb;
}

/** Convert a workbook to a File object via XLSX.write round-trip. */
function workbookToFile(wb: XLSX.WorkBook): File {
  const bytes: Uint8Array = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new File([bytes], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

// --- Property 6: Backward compatibility — full auto-import ---

describe("Property 6: Backward compatibility — full auto-import", () => {
  it("importFile returns successful Result<TabularData> without SheetSelectionNeeded or HeaderSelectionNeeded", async () => {
    // **Validates: Requirements 1.2, 6.1**
    await fc.assert(
      fc.asyncProperty(
        headerRowArb.chain((headerRow) =>
          fc
            .tuple(
              fc.constant(headerRow),
              fc.array(dataRowArb(headerRow.length), { minLength: 1, maxLength: 5 }),
              fc.uniqueArray(nonBudgetSheetName, { minLength: 0, maxLength: 3 }),
            ),
        ),
        async ([headerRow, dataRows, extraSheets]) => {
          const wb = buildBackwardCompatWorkbook(headerRow, dataRows, extraSheets);
          const file = workbookToFile(wb);

          const orchestrator = new PipelineOrchestrator();
          const result = await orchestrator.importFile(file);

          // Must NOT be SheetSelectionNeeded
          expect(isSheetSelectionNeeded(result)).toBe(false);

          // Must NOT be HeaderSelectionNeeded
          expect(isHeaderSelectionNeeded(result)).toBe(false);

          // Must be a successful result
          expect(result).toHaveProperty("ok", true);

          if ("ok" in result && result.ok) {
            // sourceName must be "Budget"
            expect(result.data.metadata.sourceName).toBe("Budget");
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
