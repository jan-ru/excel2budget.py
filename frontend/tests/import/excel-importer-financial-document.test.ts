/**
 * Tests for FinancialDocument production from Excel import.
 *
 * Validates: Requirements 3.1, 7.1
 */

import { describe, it, expect } from "vitest";
import * as XLSX from "xlsx";
import {
  extractFinancialDocument,
  tabularBudgetToFinancialDocument,
  extractBudgetData,
  extractMappingConfig,
  ParseError,
  MappingError,
} from "../../src/import/excel-importer";
import { FinancialDocumentSchema } from "../../src/types/domain";

// --- Helpers ---

function makeWorkbook(rows: unknown[][]): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, "Budget");
  return wb;
}

const VALID_ROWS = [
  ["Entity", "Account", "DC", "jan-26", "feb-26", "mrt-26"],
  ["E1", "A100", "D", 1000, 2000, 3000],
  ["E2", "A200", "C", 500, 600, 700],
];

describe("extractFinancialDocument", () => {
  it("produces a valid FinancialDocument from a budget workbook", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const result = extractFinancialDocument(wb);

    expect(result).not.toBeInstanceOf(ParseError);
    expect(result).not.toBeInstanceOf(MappingError);

    if (result instanceof ParseError || result instanceof MappingError) return;

    // Should have 6 lines (2 rows × 3 months)
    expect(result.lines).toHaveLength(6);
    expect(result.accounts).toHaveLength(2);
    expect(result.entities).toHaveLength(2);
    expect(result.meta.source).toBe("Budget");
  });

  it("all lines have line_type budget", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    for (const line of result.lines) {
      expect(line.line_type).toBe("budget");
    }
  });

  it("periods are formatted as YYYY-MM", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    const periods = new Set(result.lines.map((l) => l.period));
    expect(periods).toContain("2026-01");
    expect(periods).toContain("2026-02");
    expect(periods).toContain("2026-03");
  });

  it("amounts are serialized as decimal strings", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    for (const line of result.lines) {
      expect(typeof line.amount).toBe("string");
      expect(parseFloat(line.amount)).not.toBeNaN();
    }
  });

  it("result passes Zod validation", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    const parsed = FinancialDocumentSchema.safeParse(result);
    expect(parsed.success).toBe(true);
  });

  it("returns ParseError for missing sheet", () => {
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet([["A"]]);
    XLSX.utils.book_append_sheet(wb, ws, "Other");

    const result = extractFinancialDocument(wb);
    expect(result).toBeInstanceOf(ParseError);
  });

  it("returns MappingError for missing required columns", () => {
    const wb = makeWorkbook([["Foo", "Bar", "Baz"]]);
    const result = extractFinancialDocument(wb);
    expect(result).toBeInstanceOf(MappingError);
  });

  it("skips rows with missing account codes", () => {
    const wb = makeWorkbook([
      ["Entity", "Account", "DC", "jan-26"],
      ["E1", "A100", "D", 1000],
      ["E2", null, "C", 500],
      ["E3", "A300", "D", 300],
    ]);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    // Only 2 rows with valid accounts × 1 month = 2 lines
    expect(result.lines).toHaveLength(2);
    expect(result.accounts).toHaveLength(2);
  });

  it("handles non-numeric month values as zero", () => {
    const wb = makeWorkbook([
      ["Entity", "Account", "DC", "jan-26"],
      ["E1", "A100", "D", "not-a-number"],
    ]);
    const result = extractFinancialDocument(wb);
    if (result instanceof ParseError || result instanceof MappingError) return;

    expect(result.lines).toHaveLength(1);
    expect(parseFloat(result.lines[0].amount)).toBe(0);
  });
});

describe("tabularBudgetToFinancialDocument", () => {
  it("converts pre-extracted data and mapping to FinancialDocument", () => {
    const wb = makeWorkbook(VALID_ROWS);
    const data = extractBudgetData(wb);
    const mapping = extractMappingConfig(wb);

    if (data instanceof ParseError || mapping instanceof MappingError) {
      throw new Error("Setup failed");
    }

    const doc = tabularBudgetToFinancialDocument(data, mapping, "TestSheet");
    expect(doc.lines).toHaveLength(6);
    expect(doc.meta.source).toBe("TestSheet");

    const parsed = FinancialDocumentSchema.safeParse(doc);
    expect(parsed.success).toBe(true);
  });
});
