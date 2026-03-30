/**
 * Tests for FinancialDocument CSV and Excel export functions.
 *
 * Validates: Requirements 3.2, 3.3, 7.3, 7.4
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  financialDocumentToCsv,
  financialDocumentToAoa,
} from "../../src/export/csv-excel-exporter";
import { FinancialDocumentSchema } from "../../src/types/domain";
import { financialDocumentArb } from "../arbitraries/domain";
import type { FinancialDocument } from "../../src/types/domain";

// --- Helpers ---

function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let i = 0;
  while (i <= line.length) {
    if (i === line.length) { fields.push(""); break; }
    if (line[i] === '"') {
      let value = "";
      i++;
      while (i < line.length) {
        if (line[i] === '"') {
          if (i + 1 < line.length && line[i + 1] === '"') { value += '"'; i += 2; }
          else { i++; break; }
        } else { value += line[i]; i++; }
      }
      fields.push(value);
      if (i < line.length && line[i] === ",") i++;
    } else {
      const next = line.indexOf(",", i);
      if (next === -1) { fields.push(line.slice(i)); break; }
      else { fields.push(line.slice(i, next)); i = next + 1; }
    }
  }
  return fields;
}

function splitCsvLines(csv: string): string[] {
  const lines: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < csv.length; i++) {
    const ch = csv[i];
    if (ch === '"') { inQuotes = !inQuotes; current += ch; }
    else if (ch === "\n" && !inQuotes) { lines.push(current); current = ""; }
    else if (ch === "\r" && !inQuotes) { /* skip */ }
    else { current += ch; }
  }
  lines.push(current);
  return lines;
}

function makeDoc(lineCount: number): FinancialDocument {
  const lines = Array.from({ length: lineCount }, (_, i) => ({
    account: `A${i}`,
    entity: "E1",
    period: "2026-01",
    amount: `${(i + 1) * 100}.0000`,
    line_type: "budget" as const,
    currency: "EUR",
    memo: null,
  }));
  return FinancialDocumentSchema.parse({
    lines,
    accounts: [{ code: "A0", description: "Test", account_type: "expense", normal_balance: "D", parent_code: null }],
    entities: [{ code: "E1", description: "Entity1", is_elimination: false }],
    meta: { source: "test" },
  });
}

// --- Tests ---

describe("financialDocumentToCsv", () => {
  it("produces header + one row per line", () => {
    const doc = makeDoc(3);
    const csv = financialDocumentToCsv(doc);
    const lines = splitCsvLines(csv);
    expect(lines).toHaveLength(4); // 1 header + 3 data
  });

  it("header contains expected column names", () => {
    const doc = makeDoc(1);
    const csv = financialDocumentToCsv(doc);
    const lines = splitCsvLines(csv);
    const header = parseCsvLine(lines[0]);
    expect(header).toEqual(["account", "entity", "period", "amount", "line_type", "currency", "memo"]);
  });

  it("data rows contain correct field values", () => {
    const doc = makeDoc(1);
    const csv = financialDocumentToCsv(doc);
    const lines = splitCsvLines(csv);
    const row = parseCsvLine(lines[1]);
    expect(row[0]).toBe("A0");
    expect(row[1]).toBe("E1");
    expect(row[2]).toBe("2026-01");
    expect(row[3]).toBe("100.0000");
    expect(row[4]).toBe("budget");
    expect(row[5]).toBe("EUR");
    expect(row[6]).toBe(""); // null memo
  });

  it("empty document produces header only", () => {
    const doc = FinancialDocumentSchema.parse({
      lines: [], accounts: [], entities: [], meta: {},
    });
    const csv = financialDocumentToCsv(doc);
    const lines = splitCsvLines(csv);
    expect(lines).toHaveLength(1);
  });
});

describe("financialDocumentToAoa", () => {
  it("produces header + one row per line", () => {
    const doc = makeDoc(3);
    const aoa = financialDocumentToAoa(doc);
    expect(aoa).toHaveLength(4);
  });

  it("header row matches expected columns", () => {
    const doc = makeDoc(1);
    const aoa = financialDocumentToAoa(doc);
    expect(aoa[0]).toEqual(["account", "entity", "period", "amount", "line_type", "currency", "memo"]);
  });

  it("data rows contain correct values", () => {
    const doc = makeDoc(1);
    const aoa = financialDocumentToAoa(doc);
    expect(aoa[1][0]).toBe("A0");
    expect(aoa[1][4]).toBe("budget");
  });
});

describe("Property: FinancialDocument CSV export row count", () => {
  it("CSV row count equals lines.length + 1 (header)", () => {
    fc.assert(
      fc.property(financialDocumentArb, (rawDoc) => {
        const doc = FinancialDocumentSchema.parse(rawDoc);
        const csv = financialDocumentToCsv(doc);
        const lines = splitCsvLines(csv);
        expect(lines).toHaveLength(doc.lines.length + 1);
      }),
      { numRuns: 100 },
    );
  });

  it("AOA row count equals lines.length + 1 (header)", () => {
    fc.assert(
      fc.property(financialDocumentArb, (rawDoc) => {
        const doc = FinancialDocumentSchema.parse(rawDoc);
        const aoa = financialDocumentToAoa(doc);
        expect(aoa).toHaveLength(doc.lines.length + 1);
      }),
      { numRuns: 100 },
    );
  });
});
