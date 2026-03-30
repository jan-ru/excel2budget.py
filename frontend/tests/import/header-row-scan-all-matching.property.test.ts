// Feature: header-row-selection, Property 2: Scan finds all and only matching rows
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  scanForHeaderRow,
  rowContainsRequiredColumns,
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

/** Arbitrary for a row containing all required columns in random case, plus optional extras. */
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

/**
 * Arbitrary that generates a sheet layout with known header-row placements.
 *
 * Strategy:
 * 1. Pick a random subset of row indices (0–19) to be header rows.
 * 2. For each chosen index, generate a header row with all required columns.
 * 3. Fill remaining indices with filler rows that lack required columns.
 * 4. Optionally append extra rows beyond index 19 (never scanned).
 *
 * Returns { expectedIndices, rows } so the test can assert candidateRows === expectedIndices.
 */
const sheetWithKnownHeadersArb = fc
  .tuple(
    // Total row count between 1 and 20
    fc.integer({ min: 1, max: 20 }),
    // Which of those rows should be header rows (subset of indices)
    fc.uniqueArray(fc.integer({ min: 0, max: 19 }), {
      minLength: 0,
      maxLength: 20,
    }),
  )
  .chain(([totalRows, rawHeaderIndices]) => {
    // Clamp header indices to valid range for this sheet size
    const headerIndices = rawHeaderIndices
      .filter((i) => i < totalRows)
      .sort((a, b) => a - b);

    // Build arbitraries for each row
    const rowArbs = Array.from({ length: totalRows }, (_, i) =>
      headerIndices.includes(i) ? headerRowArb : fillerRowArb,
    );

    return fc.tuple(fc.constant(headerIndices), ...rowArbs).map(
      ([indices, ...rows]) =>
        ({
          expectedIndices: indices as number[],
          rows: rows as unknown[][],
        }),
    );
  });

// --- Property 2: Scan finds all and only matching rows ---

describe("Property 2: Scan finds all and only matching rows", () => {
  // Feature: header-row-selection, Property 2: Scan finds all and only matching rows

  it("candidateRows matches exactly the expected header row indices within the first 20 rows", () => {
    // **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    fc.assert(
      fc.property(sheetWithKnownHeadersArb, ({ expectedIndices, rows }) => {
        const wb = buildWorkbook(rows);
        const result = scanForHeaderRow(wb, "Budget");

        expect(result).not.toBeInstanceOf(ParseError);
        if (!(result instanceof ParseError)) {
          expect([...result.candidateRows].sort()).toEqual(
            [...expectedIndices].sort(),
          );
        }
      }),
      { numRuns: 100 },
    );
  });

  it("rows beyond index 19 are never included in candidateRows", () => {
    // **Validates: Requirements 2.1, 7.2**
    fc.assert(
      fc.property(
        // Generate a sheet with >20 rows, header rows only beyond index 19
        fc
          .integer({ min: 1, max: 5 })
          .chain((extraCount) => {
            const totalRows = 20 + extraCount;
            // First 20 rows are all filler, extra rows are headers
            const rowArbs: fc.Arbitrary<unknown[]>[] = [];
            for (let i = 0; i < 20; i++) rowArbs.push(fillerRowArb);
            for (let i = 0; i < extraCount; i++) rowArbs.push(headerRowArb);
            return fc.tuple(...rowArbs).map((allRows) => ({
              totalRows,
              rows: allRows,
            }));
          }),
        ({ rows }) => {
          const wb = buildWorkbook(rows);
          const result = scanForHeaderRow(wb, "Budget");

          expect(result).not.toBeInstanceOf(ParseError);
          if (!(result instanceof ParseError)) {
            // No candidates should be found since all headers are beyond row 19
            expect(result.candidateRows).toEqual([]);
            // rawPreview should contain at most 20 rows
            expect(result.rawPreview.length).toBeLessThanOrEqual(20);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("sheets with fewer than 20 rows scan only available rows without error", () => {
    // **Validates: Requirements 2.1, 7.2**
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        sheetWithKnownHeadersArb,
        (_seed, { expectedIndices, rows }) => {
          // Use a small sheet (rows.length is already 1–20)
          const wb = buildWorkbook(rows);
          const result = scanForHeaderRow(wb, "Budget");

          expect(result).not.toBeInstanceOf(ParseError);
          if (!(result instanceof ParseError)) {
            expect(result.rawPreview.length).toBe(
              Math.min(20, rows.length),
            );
            // All candidate indices must be within the actual row count
            for (const idx of result.candidateRows) {
              expect(idx).toBeLessThan(rows.length);
            }
            expect([...result.candidateRows].sort()).toEqual(
              [...expectedIndices].sort(),
            );
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
