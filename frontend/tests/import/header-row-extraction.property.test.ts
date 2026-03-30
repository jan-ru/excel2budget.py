// Feature: header-row-selection, Property 4: Extraction with header row index
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  extractBudgetData,
  ParseError,
} from "../../src/import/excel-importer";

// --- Helpers ---

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

/** Arbitrary for a header row containing all required columns in random case, plus a month column. */
const headerRowArb = fc
  .tuple(
    randomCase("Entity"),
    randomCase("Account"),
    randomCase("DC"),
    fc.array(fc.string({ minLength: 1, maxLength: 10 }), {
      minLength: 0,
      maxLength: 3,
    }),
  )
  .map(([entity, account, dc, extras]) => [entity, account, dc, "jan-26", ...extras]);

/** Arbitrary for a preamble row (non-header filler) with a fixed column count. */
const preambleRowArb = (colCount: number) =>
  fc.array(
    fc.oneof(fc.string({ minLength: 0, maxLength: 8 }), fc.integer()),
    { minLength: colCount, maxLength: colCount },
  );

/** Arbitrary for a data row with the same column count as the header. */
const dataRowArb = (colCount: number) =>
  fc.array(
    fc.oneof(fc.string({ minLength: 1, maxLength: 10 }), fc.integer()),
    { minLength: colCount, maxLength: colCount },
  );

/** Build a SheetJS workbook from a 2D array of rows. */
function buildWorkbook(rows: unknown[][], sheetName = "Budget"): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  return wb;
}

/**
 * Arbitrary that generates a sheet with a header row at a known index,
 * preamble rows before it, and data rows after it.
 *
 * Returns { headerRowIndex, headerRow, dataRows, allRows } so the test
 * can assert extraction results against the known structure.
 */
const sheetWithHeaderAtIndexArb = fc
  .integer({ min: 0, max: 19 })
  .chain((headerRowIndex) =>
    headerRowArb.chain((headerRow) => {
      const colCount = headerRow.length;
      return fc
        .tuple(
          fc.array(preambleRowArb(colCount), {
            minLength: headerRowIndex,
            maxLength: headerRowIndex,
          }),
          fc.integer({ min: 1, max: 5 }),
        )
        .chain(([preambleRows, dataRowCount]) =>
          fc
            .array(dataRowArb(colCount), {
              minLength: dataRowCount,
              maxLength: dataRowCount,
            })
            .map((dataRows) => ({
              headerRowIndex,
              headerRow,
              dataRows,
              allRows: [...preambleRows, headerRow, ...dataRows],
            })),
        );
    }),
  );

// --- Property 4: Extraction with header row index ---

describe("Property 4: Extraction with header row index", () => {
  // Feature: header-row-selection, Property 4: Extraction with header row index

  it("extractBudgetData returns columns from the header row and data rows after it", () => {
    // **Validates: Requirements 4.1, 4.2, 4.3**
    fc.assert(
      fc.property(sheetWithHeaderAtIndexArb, ({ headerRowIndex, headerRow, dataRows, allRows }) => {
        const wb = buildWorkbook(allRows);
        const result = extractBudgetData(wb, "Budget", headerRowIndex);

        // Result must not be a ParseError
        expect(result).not.toBeInstanceOf(ParseError);

        if (!(result instanceof ParseError)) {
          // Columns should match the header row
          const expectedColNames = headerRow.map((v: unknown, i: number) =>
            v != null ? String(v).trim() : `_col${i}`,
          );
          const actualColNames = result.columns.map((c) => c.name);
          expect(actualColNames).toEqual(expectedColNames);

          // Data rows should be exactly the rows after the header row
          expect(result.rows.length).toBe(dataRows.length);

          // rowCount should match the number of data rows
          expect(result.rowCount).toBe(dataRows.length);
        }
      }),
      { numRuns: 100 },
    );
  });
});
