import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { getSheetNames, hasSheet } from "../../src/import/excel-importer";
import * as XLSX from "xlsx";

// --- Helpers ---

/** Characters safe for Excel sheet names (no :\/?*[]' ) */
const SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-";

/** Arbitrary for a valid Excel sheet name (no special chars, not "Budget"). */
const validSheetName = fc
  .stringOf(fc.constantFrom(...SAFE_CHARS), { minLength: 1, maxLength: 20 })
  .map((s) => s.trim())
  .filter((s) => s.length > 0 && s !== "Budget");

/** Build a workbook with the given sheet names (each sheet has minimal content). */
function buildWorkbook(sheetNames: string[]): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  for (const name of sheetNames) {
    const ws = XLSX.utils.aoa_to_sheet([["col1"], ["val1"]]);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }
  return wb;
}

// --- Property 2: Sheet name list identity ---

describe("Property 2: Sheet name list identity", () => {
  // Feature: dynamic-sheet-selection, Property 2: Sheet name list identity

  it("getSheetNames returns the exact same array (elements and order) as workbook.SheetNames", () => {
    fc.assert(
      fc.property(
        fc.uniqueArray(validSheetName, { minLength: 1, maxLength: 8 }),
        (names) => {
          const wb = buildWorkbook(names);
          const result = getSheetNames(wb);

          expect(result).toEqual(wb.SheetNames);
          expect(result).toHaveLength(names.length);
          for (let i = 0; i < names.length; i++) {
            expect(result[i]).toBe(names[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("hasSheet returns true for every name in the workbook and false for 'Budget'", () => {
    fc.assert(
      fc.property(
        fc.uniqueArray(validSheetName, { minLength: 1, maxLength: 8 }),
        (names) => {
          const wb = buildWorkbook(names);

          for (const name of names) {
            expect(hasSheet(wb, name)).toBe(true);
          }
          expect(hasSheet(wb, "Budget")).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});
