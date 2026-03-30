// Feature: header-row-selection, Property 5: Invalid header row returns MappingError
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  extractMappingConfig,
  MappingError,
  rowContainsRequiredColumns,
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

/** Arbitrary for a filler row that does NOT contain all required columns. */
const fillerRowArb = (colCount: number) =>
  fc
    .array(
      fc.oneof(fc.string({ minLength: 0, maxLength: 8 }), fc.integer()),
      { minLength: colCount, maxLength: colCount },
    )
    .filter((row) => !rowContainsRequiredColumns(row));

/** Build a SheetJS workbook from a 2D array of rows. */
function buildWorkbook(rows: unknown[][], sheetName = "Budget"): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, sheetName);
  return wb;
}

/**
 * Arbitrary that generates a sheet with a valid header row at some index,
 * plus additional filler rows, and picks a different row index that does
 * NOT contain all required columns.
 *
 * Returns { invalidRowIndex, allRows } so the test can call
 * extractMappingConfig with the invalid index.
 */
const sheetWithInvalidHeaderIndexArb = fc
  .integer({ min: 0, max: 9 })
  .chain((headerRowIndex) =>
    headerRowArb.chain((headerRow) => {
      const colCount = headerRow.length;
      // Generate filler rows before the header
      return fc
        .tuple(
          fc.array(fillerRowArb(colCount), {
            minLength: headerRowIndex,
            maxLength: headerRowIndex,
          }),
          fc.array(fillerRowArb(colCount), { minLength: 1, maxLength: 5 }),
        )
        .map(([preambleRows, trailingRows]) => {
          const allRows = [...preambleRows, headerRow, ...trailingRows];
          // Collect indices of rows that do NOT have required columns
          const invalidIndices = allRows
            .map((row, i) => ({ row, i }))
            .filter(({ row }) => !rowContainsRequiredColumns(row))
            .map(({ i }) => i);
          return { allRows, invalidIndices };
        })
        .filter(({ invalidIndices }) => invalidIndices.length > 0)
        .chain(({ allRows, invalidIndices }) =>
          fc
            .integer({ min: 0, max: invalidIndices.length - 1 })
            .map((pick) => ({
              invalidRowIndex: invalidIndices[pick],
              allRows,
            })),
        );
    }),
  );

// --- Property 5: Invalid header row returns MappingError ---

describe("Property 5: Invalid header row returns MappingError", () => {
  // Feature: header-row-selection, Property 5: Invalid header row returns MappingError

  it("extractMappingConfig returns MappingError with non-empty missingColumns for a non-header row", () => {
    // **Validates: Requirements 4.4**
    fc.assert(
      fc.property(sheetWithInvalidHeaderIndexArb, ({ invalidRowIndex, allRows }) => {
        const wb = buildWorkbook(allRows);
        const result = extractMappingConfig(wb, "Budget", invalidRowIndex);

        // Result must be a MappingError
        expect(result).toBeInstanceOf(MappingError);

        if (result instanceof MappingError) {
          // missingColumns must be non-empty
          expect(result.missingColumns.length).toBeGreaterThan(0);
        }
      }),
      { numRuns: 100 },
    );
  });
});
