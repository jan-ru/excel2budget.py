// Feature: header-row-selection, Property 1: Row 0 auto-detection
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  scanForHeaderRow,
  rowContainsRequiredColumns,
  ParseError,
} from "../../src/import/excel-importer";

// --- Helpers ---

const REQUIRED = ["Entity", "Account", "DC"] as const;

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

/** Arbitrary for a row-0 header containing all required columns in random case, plus optional extras. */
const headerRowArb = fc
  .tuple(
    randomCase("Entity"),
    randomCase("Account"),
    randomCase("DC"),
    fc.array(fc.string({ minLength: 1, maxLength: 10 }), {
      minLength: 0,
      maxLength: 5,
    }),
  )
  .map(([entity, account, dc, extras]) =>
    fc.shuffledSubarray([entity, account, dc, ...extras], {
      minLength: 3 + extras.length,
      maxLength: 3 + extras.length,
    }),
  )
  .chain((arb) => arb);

/** Arbitrary for a filler data row that does NOT contain all required columns. */
const fillerRowArb = fc
  .array(fc.oneof(fc.string({ minLength: 0, maxLength: 8 }), fc.integer()), {
    minLength: 1,
    maxLength: 6,
  })
  .filter((row) => !rowContainsRequiredColumns(row));

/** Build a SheetJS workbook from a 2D array of rows. */
function buildWorkbook(rows: unknown[][], sheetName = "Budget"): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  return wb;
}

// --- Property 1: Row 0 auto-detection ---

describe("Property 1: Row 0 auto-detection", () => {
  // Feature: header-row-selection, Property 1: Row 0 auto-detection

  it("scanForHeaderRow returns candidateRows including 0 when row 0 has all required columns in any case", () => {
    // **Validates: Requirements 1.1**
    fc.assert(
      fc.property(
        headerRowArb,
        fc.array(fillerRowArb, { minLength: 0, maxLength: 5 }),
        (headerRow, dataRows) => {
          const rows = [headerRow, ...dataRows];
          const wb = buildWorkbook(rows);

          const result = scanForHeaderRow(wb, "Budget");
          expect(result).not.toBeInstanceOf(ParseError);

          if (!(result instanceof ParseError)) {
            expect(result.candidateRows).toContain(0);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
