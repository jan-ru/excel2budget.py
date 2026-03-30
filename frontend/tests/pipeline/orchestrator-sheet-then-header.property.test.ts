// Feature: header-row-selection, Property 7: Sheet selection then auto header detection
/**
 * Property 7: Sheet selection then auto header detection
 *
 * For any workbook without a "Budget" sheet but containing a sheet with
 * Required_Columns in row 0 (plus valid month columns and data), after sheet
 * selection via `importWithSheet`, the result SHALL be a successful
 * `Result<TabularData>` without returning `HeaderSelectionNeeded`.
 *
 * **Validates: Requirements 6.2**
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
 * Build a workbook WITHOUT a "Budget" sheet. Each sheet has the given header
 * row in row 0 and at least one data row. The target sheet (at targetIndex)
 * uses the provided headerRow and dataRows; other sheets get minimal content.
 */
function buildWorkbookWithoutBudget(
  sheetNames: string[],
  targetIndex: number,
  headerRow: unknown[],
  dataRows: unknown[][],
): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  for (let i = 0; i < sheetNames.length; i++) {
    if (i === targetIndex) {
      const sheetData = [headerRow, ...dataRows];
      const ws = XLSX.utils.aoa_to_sheet(sheetData);
      XLSX.utils.book_append_sheet(wb, ws, sheetNames[i]);
    } else {
      // Other sheets get valid headers + one data row too
      const ws = XLSX.utils.aoa_to_sheet([headerRow, headerRow.map(() => "x")]);
      XLSX.utils.book_append_sheet(wb, ws, sheetNames[i]);
    }
  }

  return wb;
}

/** Convert a workbook to a File object via XLSX.write round-trip. */
function workbookToFile(wb: XLSX.WorkBook): File {
  const bytes = XLSX.write(wb, { type: "array", bookType: "xlsx" }) as Uint8Array;
  return new File([bytes as BlobPart], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

// --- Property 7: Sheet selection then auto header detection ---

describe("Property 7: Sheet selection then auto header detection", () => {
  it("importWithSheet returns successful result without HeaderSelectionNeeded when headers are in row 0", async () => {
    // **Validates: Requirements 6.2**
    await fc.assert(
      fc.asyncProperty(
        headerRowArb.chain((headerRow) =>
          fc
            .tuple(
              fc.constant(headerRow),
              fc.uniqueArray(nonBudgetSheetName, { minLength: 1, maxLength: 5 }),
              fc.array(dataRowArb(headerRow.length), { minLength: 1, maxLength: 5 }),
            )
            .chain(([hr, names, dataRows]) =>
              fc.record({
                headerRow: fc.constant(hr),
                sheetNames: fc.constant(names),
                dataRows: fc.constant(dataRows),
                targetIndex: fc.nat({ max: names.length - 1 }),
              }),
            ),
        ),
        async ({ headerRow, sheetNames, dataRows, targetIndex }) => {
          const selectedSheet = sheetNames[targetIndex];
          const wb = buildWorkbookWithoutBudget(sheetNames, targetIndex, headerRow, dataRows);
          const file = workbookToFile(wb);

          const orchestrator = new PipelineOrchestrator();

          // Step 1: importFile should return SheetSelectionNeeded (no "Budget" sheet)
          const importResult = await orchestrator.importFile(file);
          expect(isSheetSelectionNeeded(importResult)).toBe(true);

          // Step 2: importWithSheet with the selected sheet name
          const result = await orchestrator.importWithSheet(selectedSheet);

          // Must NOT be HeaderSelectionNeeded (headers are in row 0)
          expect(isHeaderSelectionNeeded(result)).toBe(false);

          // Must be a successful result
          expect(result).toHaveProperty("ok", true);

          if ("ok" in result && result.ok) {
            // sourceName must equal the selected sheet name
            expect(result.data.metadata.sourceName).toBe(selectedSheet);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
