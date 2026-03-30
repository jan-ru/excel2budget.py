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
import {
  FinancialDocumentSchema,
  type FinancialDocument,
  type FinancialLine,
  type Account,
  type Entity,
} from "../types/domain";

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
 * Extract budget data from the named sheet, using the specified header row.
 * @param headerRowIndex Zero-based index of the row to use as column headers.
 *   Defaults to 0 for backward compatibility.
 * Returns a ParseError if the sheet does not exist or is empty.
 */
export function extractBudgetData(
  workbook: XLSX.WorkBook,
  sheetName = "Budget",
  headerRowIndex = 0,
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

  const headerRow = raw[headerRowIndex] ?? [];
  const colNames = headerRow.map((v, i) =>
    v != null ? String(v).trim() : `_col${i}`,
  );

  const columns: ColumnDef[] = colNames.map((name) => ({
    name,
    dataType: "STRING",
    nullable: true,
  }));

  const rows: Row[] = [];
  for (let r = headerRowIndex + 1; r < raw.length; r++) {
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
 * Extract column mapping configuration from the specified header row.
 * Identifies Entity, Account, DC columns and Dutch month columns.
 * @param headerRowIndex Zero-based index of the row to use as column headers.
 *   Defaults to 0 for backward compatibility.
 */
export function extractMappingConfig(
  workbook: XLSX.WorkBook,
  sheetName = "Budget",
  headerRowIndex = 0,
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

  const headerRow = raw[headerRowIndex] ?? [];
  const colNames = headerRow.map((v, i) =>
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

/**
 * Extract a Zod-validated FinancialDocument from a workbook sheet.
 *
 * Parses budget rows into FinancialLine objects (one per account × entity × period),
 * extracts Account and Entity dimensions, and validates the result with
 * FinancialDocumentSchema.parse().
 *
 * @param workbook Parsed SheetJS workbook.
 * @param sheetName Sheet to read (default "Budget").
 * @param headerRowIndex Zero-based header row index (default 0).
 * @returns A validated FinancialDocument or a ParseError/MappingError.
 */
export function extractFinancialDocument(
  workbook: XLSX.WorkBook,
  sheetName = "Budget",
  headerRowIndex = 0,
): FinancialDocument | ParseError | MappingError {
  const data = extractBudgetData(workbook, sheetName, headerRowIndex);
  if (data instanceof ParseError) return data;

  const mapping = extractMappingConfig(workbook, sheetName, headerRowIndex);
  if (mapping instanceof MappingError) return mapping;

  return tabularBudgetToFinancialDocument(data, mapping, sheetName);
}

/**
 * Convert already-extracted TabularData + MappingConfig into a FinancialDocument.
 * Useful when data and mapping have already been extracted separately.
 */
export function tabularBudgetToFinancialDocument(
  data: TabularData,
  mapping: MappingConfig,
  sourceName = "Budget",
): FinancialDocument {
  const entityIdx = data.columns.findIndex((c) => c.name === mapping.entityColumn);
  const accountIdx = data.columns.findIndex((c) => c.name === mapping.accountColumn);
  const dcIdx = data.columns.findIndex((c) => c.name === mapping.dcColumn);

  const monthIndices = mapping.monthColumns.map((mc) => ({
    colIdx: data.columns.findIndex((c) => c.name === mc.sourceColumnName),
    periodNumber: mc.periodNumber,
    year: mc.year,
  }));

  const lines: FinancialLine[] = [];
  const accountSet = new Map<string, Account>();
  const entitySet = new Map<string, Entity>();

  for (const row of data.rows) {
    const accountRaw = cellToString(row.values[accountIdx]);
    if (!accountRaw) continue; // skip rows with missing account

    const entityRaw = cellToString(row.values[entityIdx]);
    const dcRaw = cellToString(row.values[dcIdx]);
    const normalBalance = dcRaw === "C" || dcRaw === "D" ? dcRaw : "D";

    // Register account dimension
    if (!accountSet.has(accountRaw)) {
      accountSet.set(accountRaw, {
        code: accountRaw as Account["code"],
        description: accountRaw,
        account_type: "expense",
        normal_balance: normalBalance as Account["normal_balance"],
        parent_code: null,
      });
    }

    // Register entity dimension
    if (entityRaw && !entitySet.has(entityRaw)) {
      entitySet.set(entityRaw, {
        code: entityRaw as Entity["code"],
        description: entityRaw,
        is_elimination: false,
      });
    }

    // Create one BudgetLine per month column
    for (const mc of monthIndices) {
      if (mc.colIdx < 0) continue;
      const rawAmount = cellToNumber(row.values[mc.colIdx]);
      const period = `${mc.year}-${String(mc.periodNumber).padStart(2, "0")}`;

      lines.push({
        account: accountRaw as FinancialLine["account"],
        entity: (entityRaw || "") as FinancialLine["entity"],
        period,
        amount: rawAmount.toFixed(4),
        line_type: "budget",
        currency: "EUR",
        memo: null,
      });
    }
  }

  const doc = {
    lines,
    accounts: [...accountSet.values()],
    entities: [...entitySet.values()],
    meta: { source: sourceName },
  };

  return FinancialDocumentSchema.parse(doc);
}

// --- Sheet helpers ---

/**
 * Get the list of sheet names from a parsed workbook.
 * Returns an empty array if the workbook has no sheets.
 */
export function getSheetNames(workbook: XLSX.WorkBook): string[] {
  return workbook.SheetNames;
}

/**
 * Check whether a specific sheet exists in the workbook.
 */
export function hasSheet(workbook: XLSX.WorkBook, name: string): boolean {
  return workbook.SheetNames.includes(name);
}

// --- Header row scanning ---

/** Result of scanning a sheet for header rows. */
export interface HeaderScanResult {
  /** Zero-based indices of rows containing all required columns. */
  candidateRows: number[];
  /** First 20 rows of raw data for preview (each row is an array of cell values). */
  rawPreview: unknown[][];
}

/**
 * Check if a row contains all required columns using case-insensitive matching.
 * Exported for direct testing in property tests.
 */
export function rowContainsRequiredColumns(
  row: unknown[],
  requiredColumns: readonly string[] = REQUIRED_COLUMNS,
): boolean {
  const cells = row.map((v) => (v != null ? String(v).trim().toLowerCase() : ""));
  return requiredColumns.every((req) => cells.includes(req.toLowerCase()));
}

/**
 * Scan the first 20 rows of a sheet for rows containing all required columns.
 * Uses case-insensitive matching consistent with extractMappingConfig.
 * If the sheet has fewer than 20 rows, scans all available rows.
 */
export function scanForHeaderRow(
  workbook: XLSX.WorkBook,
  sheetName: string,
): HeaderScanResult | ParseError {
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
  });

  if (raw.length === 0) {
    return new ParseError(`Sheet '${sheetName}' is empty`, available);
  }

  const scanLimit = Math.min(20, raw.length);
  const candidateRows: number[] = [];

  for (let i = 0; i < scanLimit; i++) {
    if (rowContainsRequiredColumns(raw[i])) {
      candidateRows.push(i);
    }
  }

  return {
    candidateRows,
    rawPreview: raw.slice(0, scanLimit),
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

function cellToString(cell: CellValue): string {
  if (cell.type === "null") return "";
  if (cell.type === "string") return cell.value;
  return String((cell as { value: unknown }).value);
}

function cellToNumber(cell: CellValue): number {
  if (cell.type === "int" || cell.type === "float") return cell.value;
  if (cell.type === "string") {
    const n = parseFloat(cell.value);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}
