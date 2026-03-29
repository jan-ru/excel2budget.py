import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  tabularDataToCsv,
  tabularDataToAoa,
  cellValueToString,
} from "../../src/export/csv-excel-exporter";
import type { components } from "../../src/types/api";

type TabularData = components["schemas"]["TabularData"];
type CellValue = components["schemas"]["Row"]["values"][number];
type ColumnDef = components["schemas"]["ColumnDef"];
type Row = components["schemas"]["Row"];

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generate a safe column name (no commas/newlines to keep CSV parsing simple). */
const arbColumnName = fc
  .stringOf(fc.constantFrom(..."abcdefghijklmnopqrstuvwxyz0123456789_"), {
    minLength: 1,
    maxLength: 20,
  })
  .filter((s) => s.length > 0);

/** Generate a CellValue. */
const arbCellValue: fc.Arbitrary<CellValue> = fc.oneof(
  fc
    .string({ minLength: 0, maxLength: 30 })
    .map((v) => ({ type: "string" as const, value: v })),
  fc.integer().map((v) => ({ type: "int" as const, value: v })),
  fc
    .double({ noNaN: true, noDefaultInfinity: true })
    .map((v) => ({ type: "float" as const, value: v })),
  fc.boolean().map((v) => ({ type: "bool" as const, value: v })),
  fc.constant({ type: "null" as const }),
);

/** Generate a valid TabularData with consistent column count. */
function arbTabularData(
  maxCols: number = 5,
  maxRows: number = 10,
): fc.Arbitrary<TabularData> {
  return fc
    .integer({ min: 1, max: maxCols })
    .chain((numCols) => {
      const colDefs: fc.Arbitrary<ColumnDef[]> = fc.array(
        arbColumnName.map((name) => ({
          name,
          dataType: "STRING" as const,
          nullable: true,
        })),
        { minLength: numCols, maxLength: numCols },
      );

      const rows: fc.Arbitrary<Row[]> = fc.array(
        fc
          .array(arbCellValue, { minLength: numCols, maxLength: numCols })
          .map((values) => ({ values })),
        { minLength: 0, maxLength: maxRows },
      );

      return fc.tuple(colDefs, rows).map(([columns, rows]) => ({
        columns,
        rows,
        rowCount: rows.length,
        metadata: {
          sourceName: "",
          sourceFormat: "EXCEL" as const,
          importedAt: null,
          transformedAt: null,
          exportedAt: null,
          encoding: "utf-8",
        },
      }));
    });
}

// ---------------------------------------------------------------------------
// Minimal CSV parser (for round-trip verification)
// ---------------------------------------------------------------------------

function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let i = 0;
  while (i <= line.length) {
    if (i === line.length) {
      fields.push("");
      break;
    }
    if (line[i] === '"') {
      // Quoted field
      let value = "";
      i++; // skip opening quote
      while (i < line.length) {
        if (line[i] === '"') {
          if (i + 1 < line.length && line[i + 1] === '"') {
            value += '"';
            i += 2;
          } else {
            i++; // skip closing quote
            break;
          }
        } else {
          value += line[i];
          i++;
        }
      }
      fields.push(value);
      if (i < line.length && line[i] === ",") i++; // skip comma
    } else {
      // Unquoted field
      const next = line.indexOf(",", i);
      if (next === -1) {
        fields.push(line.slice(i));
        break;
      } else {
        fields.push(line.slice(i, next));
        i = next + 1;
      }
    }
  }
  return fields;
}

/**
 * Split CSV text into lines, respecting quoted fields that contain newlines.
 * Handles trailing newlines correctly — a trailing \n does NOT produce an
 * extra empty line (matches the join("\n") output convention).
 */
function splitCsvLines(csv: string): string[] {
  const lines: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < csv.length; i++) {
    const ch = csv[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
      current += ch;
    } else if (ch === "\n" && !inQuotes) {
      lines.push(current);
      current = "";
    } else if (ch === "\r" && !inQuotes) {
      // skip \r
    } else {
      current += ch;
    }
  }
  // Always push the last segment — even if empty (represents a real row)
  lines.push(current);
  return lines;
}

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

describe("Property 13: CSV/Excel Export Round-Trip", () => {
  it("CSV export preserves column names", () => {
    fc.assert(
      fc.property(arbTabularData(), (data) => {
        const csv = tabularDataToCsv(data);
        const lines = splitCsvLines(csv);
        expect(lines.length).toBeGreaterThanOrEqual(1);
        const headerFields = parseCsvLine(lines[0]);
        expect(headerFields).toEqual(data.columns.map((c) => c.name));
      }),
      { numRuns: 100 },
    );
  });

  it("CSV export preserves row count", () => {
    fc.assert(
      fc.property(arbTabularData(), (data) => {
        const csv = tabularDataToCsv(data);
        const lines = splitCsvLines(csv);
        // First line is header, rest are data rows
        expect(lines.length - 1).toBe(data.rows.length);
      }),
      { numRuns: 100 },
    );
  });

  it("CSV export preserves string representations of cell values", () => {
    fc.assert(
      fc.property(arbTabularData(3, 5), (data) => {
        const csv = tabularDataToCsv(data);
        const lines = splitCsvLines(csv);
        for (let r = 0; r < data.rows.length; r++) {
          const fields = parseCsvLine(lines[r + 1]);
          for (let c = 0; c < data.columns.length; c++) {
            const expected = cellValueToString(data.rows[r].values[c]);
            expect(fields[c]).toBe(expected);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it("AOA (Excel) export preserves column names and row count", () => {
    fc.assert(
      fc.property(arbTabularData(), (data) => {
        const aoa = tabularDataToAoa(data);
        // First row is header
        expect(aoa[0]).toEqual(data.columns.map((c) => c.name));
        // Remaining rows match data row count
        expect(aoa.length - 1).toBe(data.rows.length);
      }),
      { numRuns: 100 },
    );
  });

  it("AOA (Excel) export preserves string representations", () => {
    fc.assert(
      fc.property(arbTabularData(3, 5), (data) => {
        const aoa = tabularDataToAoa(data);
        for (let r = 0; r < data.rows.length; r++) {
          for (let c = 0; c < data.columns.length; c++) {
            const expected = cellValueToString(data.rows[r].values[c]);
            expect(aoa[r + 1][c]).toBe(expected);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it("cellValueToString handles all CellValue types", () => {
    expect(cellValueToString({ type: "string", value: "hello" })).toBe("hello");
    expect(cellValueToString({ type: "int", value: 42 })).toBe("42");
    expect(cellValueToString({ type: "float", value: 3.14 })).toBe("3.14");
    expect(cellValueToString({ type: "bool", value: true })).toBe("true");
    expect(cellValueToString({ type: "bool", value: false })).toBe("false");
    expect(cellValueToString({ type: "date", value: "2025-01-15" })).toBe("2025-01-15");
    expect(cellValueToString({ type: "null" })).toBe("");
  });
});
