/**
 * Client-side Excel budget file importer.
 *
 * Parses .xlsx files using SheetJS, extracts budget data and column mapping
 * configuration. Detects month columns using Dutch month name conventions.
 * All processing happens in the browser — no data is sent to any server.
 *
 * Requirements: 7.1, 7.2, 7.3, 7.4
 */

import * as XLSX from "xlsx";
import type { components } from "../types/api";

// --- Type aliases from generated API types ---
type TabularData = components["schemas"]["TabularData"];
type ColumnDef = components["schemas"]["ColumnDef"];
type Row = components["schemas"]["Row"];
type CellValue = Row["values"][number];
type MappingConfig = components["schemas"]["MappingConfig"];
type MonthColumnDef = components["schemas"]["MonthColumnDef"];

// --- Error types ---

export class ParseError extends Error {
  constructor(
    message: string,
    public readonly availableSheets: string[] = [],
  ) {
    super(message);
    this.name = "ParseError";
  }
}

export class MappingError extends Error {
  constructor(
    message: string,
    public readonly missingColumns: string[] = [],
    public readonly availableColumns: string[] = [],
  ) {
    super(message);
    this.name = "MappingError";
  }
}

// --- Constants ---

/** Dutch month abbreviations (index 0 = January). */
export const DUTCH_MONTHS: readonly string[] = [
  "jan", "feb", "mrt", "apr", "mei", "jun",
  "jul", "aug", "sep", "okt", "nov", "dec",
];

const REQUIRED_COLUMNS = ["Entity", "Account", "DC"] as const;

/** Pattern: "jan-26", "feb-2026", "mrt-24", etc. */
const MONTH_COLUMN_PATTERN = new RegExp(
  `^(${DUTCH_MONTHS.join("|")})-(\\d{2,4})$`,
  "i",
);

// --- Public API ---

/**
 * Parse raw bytes into a SheetJS workbook.
 * Returns a ParseError if the bytes are not a valid .xlsx file.
 */
export function parseExcelFile(
  rawBytes: ArrayBuffer | Uint8Array,
): XLSX.WorkBook | ParseError {
  try {
    return XLSX.read(rawBytes, { type: "array" });
  } catch (exc) {
    return new ParseError(
      `Expected a valid .xlsx file, but parsing failed: ${exc instanceof Error ? exc.message : String(exc)}`,
    );
  }
}

/**
 * Extract budget data from the named sheet.
 * Returns a ParseError if the sheet does not exist or is empty.
 */
export function extractBudgetData(
  workbook: XLSX.WorkBook,
  sheetName = "Budget",
): TabularData | ParseError {
  const available = workbook.SheetNames;
  if (!available.includes(sheetName)) {
    return new ParseError(
      `Sheet '${sheetName}' not found in workbook`,
      available,
    );
  }

  const ws = workbook.Sheets[sheetName];
  const raw: unknown[][] = XLSX.utils.sheet_to_json(ws, {
    header: 1,
    defval: null,
    blankrows: false,
  });

  if (raw.length === 0) {
    return new ParseError(`Sheet '${sheetName}' is empty`, available);
  }

  const headerRow = raw[0];
  const colNames = headerRow.map((v, i) =>
    v != null ? String(v).trim() : `_col${i}`,
  );

  const columns: ColumnDef[] = colNames.map((name) => ({
    name,
    dataType: "STRING",
    nullable: true,
  }));

  const rows: Row[] = [];
  for (let r = 1; r < raw.length; r++) {
    const rawRow = raw[r];
    const values: CellValue[] = [];
    for (let c = 0; c < columns.length; c++) {
      values.push(cellToValue(c < rawRow.length ? rawRow[c] : null));
    }
    rows.push({ values });
  }

  return {
    columns,
    rows,
    rowCount: rows.length,
    metadata: {
      sourceName: sheetName,
      sourceFormat: "EXCEL",
      importedAt: null,
      transformedAt: null,
      exportedAt: null,
      encoding: "utf-8",
    },
  };
}

/**
 * Extract column mapping configuration from the budget sheet headers.
 * Identifies Entity, Account, DC columns and Dutch month columns.
 */
export function extractMappingConfig(
  workbook: XLSX.WorkBook,
  sheetName = "Budget",
): MappingConfig | MappingError {
  const available = workbook.SheetNames;
  if (!available.includes(sheetName)) {
    return new MappingError(`Sheet '${sheetName}' not found`, [], []);
  }

  const ws = workbook.Sheets[sheetName];
  const raw: unknown[][] = XLSX.utils.sheet_to_json(ws, {
    header: 1,
    defval: null,
  });

  if (raw.length === 0) {
    return new MappingError(`Sheet '${sheetName}' is empty`);
  }

  const colNames = raw[0].map((v, i) =>
    v != null ? String(v).trim() : `_col${i}`,
  );

  // Find required columns
  const missing: string[] = [];
  const found: Record<string, string> = {};
  for (const req of REQUIRED_COLUMNS) {
    const match = findColumn(req, colNames);
    if (match == null) {
      missing.push(req);
    } else {
      found[req] = match;
    }
  }

  if (missing.length > 0) {
    return new MappingError(
      `Required columns not found: ${missing.sort().join(", ")}`,
      missing.sort(),
      colNames,
    );
  }

  const monthCols = detectMonthColumnsFromHeaders(colNames);
  if (monthCols.length === 0) {
    return new MappingError(
      "No month columns detected. Expected columns like 'jan-26', 'feb-26', etc.",
      [],
      colNames,
    );
  }

  return {
    entityColumn: found["Entity"],
    accountColumn: found["Account"],
    dcColumn: found["DC"],
    monthColumns: monthCols,
  };
}

// --- Exported helpers (for testing) ---

/**
 * Detect month columns from header names using the Dutch month pattern.
 * Exported for direct testing in property tests.
 */
export function detectMonthColumnsFromHeaders(
  colNames: string[],
): MonthColumnDef[] {
  const results: MonthColumnDef[] = [];
  for (const name of colNames) {
    const trimmed = name.trim();
    const match = MONTH_COLUMN_PATTERN.exec(trimmed);
    if (match) {
      const monthAbbr = match[1].toLowerCase();
      const yearStr = match[2];
      const period = DUTCH_MONTHS.indexOf(monthAbbr) + 1;
      const year = normalizeYear(parseInt(yearStr, 10));
      results.push({
        sourceColumnName: trimmed,
        periodNumber: period,
        year,
      });
    }
  }
  results.sort((a, b) => a.periodNumber - b.periodNumber);
  return results;
}

// --- Internal helpers ---

function cellToValue(raw: unknown): CellValue {
  if (raw == null) return { type: "null" };
  if (typeof raw === "boolean") return { type: "string", value: String(raw) };
  if (typeof raw === "number") {
    return Number.isInteger(raw)
      ? { type: "int", value: raw }
      : { type: "float", value: raw };
  }
  return { type: "string", value: String(raw) };
}

function findColumn(required: string, colNames: string[]): string | null {
  // Exact match first
  const exact = colNames.find((n) => n === required);
  if (exact != null) return exact;
  // Case-insensitive fallback
  const lower = required.toLowerCase();
  const ci = colNames.find((n) => n.toLowerCase() === lower);
  return ci ?? null;
}

function normalizeYear(year: number): number {
  return year < 100 ? 2000 + year : year;
}
