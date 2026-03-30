/**
 * Pipeline orchestrator for the frontend data conversion flow.
 *
 * Coordinates: file import → Memory_Guard → Excel_Importer → Data_Validator
 * → API_Client.getTemplate → SQL_Generator → DuckDB_WASM.execute → result.
 *
 * All session state is held in-memory (ephemeral, no persistence).
 * Halts on first error and returns a descriptive error to the caller.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 2.4, 2.5
 */

import type { components } from "../types/api";
import type { Result } from "../api/client";
import type { FinancialDocument } from "../types/domain";
import { validateFileSize } from "../guards/memory-guard";
import * as XLSX from "xlsx";
import {
  parseExcelFile,
  extractBudgetData,
  extractMappingConfig,
  tabularBudgetToFinancialDocument,
  scanForHeaderRow,
  getSheetNames,
  hasSheet,
  ParseError,
  MappingError,
} from "../import/excel-importer";
import {
  validateMappingConfig,
  validateUserParams,
  validateDCValues,
} from "../validation/data-validator";
import { getTemplate } from "../api/client";
import { generateTransformSql, SQLGenerationError } from "../transform/sql-generator";
import * as duckdb from "../engine/duckdb-engine";

// --- Type aliases ---
type TabularData = components["schemas"]["TabularData"];
type MappingConfig = components["schemas"]["MappingConfig"];
type OutputTemplate = components["schemas"]["OutputTemplate"];
type UserParams = components["schemas"]["UserParams"];

// --- Sheet selection types ---

/** Returned when the user must select a sheet before import can proceed. */
export interface SheetSelectionNeeded {
  needsSelection: true;
  sheetNames: string[];
}

/** Returned when the user must select a header row. */
export interface HeaderSelectionNeeded {
  needsHeaderSelection: true;
  /** Zero-based candidate row indices (may be empty). */
  candidateRows: number[];
  /** First 20 rows of raw sheet data for preview display. */
  rawPreview: unknown[][];
}

/** Union of possible import outcomes. */
export type ImportResult = Result<TabularData> | SheetSelectionNeeded | HeaderSelectionNeeded;

/** Type guard for SheetSelectionNeeded. */
export function isSheetSelectionNeeded(
  result: ImportResult,
): result is SheetSelectionNeeded {
  return "needsSelection" in result && (result as SheetSelectionNeeded).needsSelection === true;
}

/** Type guard for HeaderSelectionNeeded. */
export function isHeaderSelectionNeeded(
  result: ImportResult,
): result is HeaderSelectionNeeded {
  return "needsHeaderSelection" in result && (result as HeaderSelectionNeeded).needsHeaderSelection === true;
}

// --- Pipeline step names (for error reporting) ---
export type PipelineStep =
  | "memory_guard"
  | "excel_parse"
  | "extract_data"
  | "extract_mapping"
  | "validate_mapping"
  | "validate_params"
  | "validate_dc"
  | "fetch_template"
  | "sql_generation"
  | "duckdb_execute";

export class PipelineError extends Error {
  constructor(
    message: string,
    public readonly step: PipelineStep,
  ) {
    super(message);
    this.name = "PipelineError";
  }
}

/** Tracks which steps have executed (for testing/observability). */
export interface PipelineTrace {
  executedSteps: PipelineStep[];
  failedStep: PipelineStep | null;
}

/**
 * Pipeline orchestrator — coordinates the full client-side conversion flow.
 *
 * All data is held in-memory and released when the instance is discarded.
 * No data is persisted to disk, localStorage, or transmitted to any server
 * (except metadata sent to the backend documentation endpoint).
 */
export class PipelineOrchestrator {
  // Session state (ephemeral)
  private _pendingWorkbook: XLSX.WorkBook | null = null;
  private _pendingSheetName: string | null = null;
  private _sourceData: TabularData | null = null;
  private _financialDocument: FinancialDocument | null = null;
  private _mappingConfig: MappingConfig | null = null;
  private _template: OutputTemplate | null = null;
  private _userParams: UserParams | null = null;
  private _transformResult: TabularData | null = null;
  private _generatedSql: string | null = null;
  private _trace: PipelineTrace = { executedSteps: [], failedStep: null };

  // --- Accessors (read-only) ---
  get sourceData(): TabularData | null { return this._sourceData; }
  /** The FinancialDocument produced from the imported budget data. */
  get financialDocument(): FinancialDocument | null { return this._financialDocument; }
  get mappingConfig(): MappingConfig | null { return this._mappingConfig; }
  get template(): OutputTemplate | null { return this._template; }
  get userParams(): UserParams | null { return this._userParams; }
  get transformResult(): TabularData | null { return this._transformResult; }
  get generatedSql(): string | null { return this._generatedSql; }
  get trace(): PipelineTrace { return { ...this._trace, executedSteps: [...this._trace.executedSteps] }; }

  /**
   * Import a file: validate size, parse Excel, extract data + mapping.
   * Returns SheetSelectionNeeded when no "Budget" sheet exists.
   * Halts on first error.
   */
  async importFile(file: File): Promise<ImportResult> {
    this._resetTrace();

    // Step 1: Memory guard
    try {
      this._markStep("memory_guard");
      validateFileSize(file.size);
    } catch (err) {
      return this._fail("memory_guard", (err as Error).message);
    }

    // Step 2: Parse Excel
    this._markStep("excel_parse");
    const buffer = await file.arrayBuffer();
    const workbook = parseExcelFile(new Uint8Array(buffer));
    if (workbook instanceof ParseError) {
      return this._fail("excel_parse", workbook.message);
    }

    // Step 2b: Check for zero sheets
    const sheetNames = getSheetNames(workbook);
    if (sheetNames.length === 0) {
      return this._fail("excel_parse", "Workbook contains no sheets");
    }

    // Step 2c: Check for "Budget" sheet
    if (!hasSheet(workbook, "Budget")) {
      this._pendingWorkbook = workbook;
      return { needsSelection: true, sheetNames };
    }

    // Step 3: Scan for header row
    return this._resolveHeaderRow(workbook, "Budget");
  }

  /**
   * Import data from a specific sheet in the pending workbook.
   * Call this after `importFile` returns `SheetSelectionNeeded`.
   * On success, releases the pending workbook. On failure, keeps it
   * so the user can retry with a different sheet.
   */
  async importWithSheet(sheetName: string): Promise<ImportResult> {
    if (this._pendingWorkbook == null) {
      return this._fail("extract_data", "No pending workbook. Call importFile() first.");
    }

    return this._resolveHeaderRow(this._pendingWorkbook, sheetName);
  }

  /**
   * Import data using a user-selected header row from the pending workbook/sheet.
   * Call this after `importFile` or `importWithSheet` returns `HeaderSelectionNeeded`.
   * On success, clears pending state. On failure, keeps pending state so user can retry.
   */
  async importWithHeaderRow(headerRowIndex: number): Promise<Result<TabularData>> {
    if (this._pendingWorkbook == null || this._pendingSheetName == null) {
      return this._fail("extract_data", "No pending import. Call importFile() first.");
    }

    return this._extractWithHeaderRow(this._pendingWorkbook, this._pendingSheetName, headerRowIndex);
  }

  /**
   * Set user parameters (budgetcode, year).
   */
  setParams(budgetcode: string, year: number): void {
    this._userParams = { budgetcode, year };
  }

  /**
   * Select a template by fetching it from the backend API.
   */
  async selectTemplate(pkg: string, tpl: string): Promise<Result<OutputTemplate>> {
    const result = await getTemplate(pkg, tpl);
    if (result.ok) {
      this._template = result.data;
    }
    return result;
  }

  /**
   * Run the full transformation pipeline.
   *
   * Validates → fetches template → generates SQL → executes in DuckDB-WASM.
   * Halts on first error. Requires importFile() and setParams() to have been
   * called first.
   */
  async runTransform(): Promise<Result<TabularData>> {
    this._resetTrace();

    if (!this._sourceData || !this._mappingConfig) {
      return this._fail("validate_mapping", "No data imported. Call importFile() first.");
    }
    if (!this._userParams) {
      return this._fail("validate_params", "No user params set. Call setParams() first.");
    }

    // Step 1: Validate mapping config
    this._markStep("validate_mapping");
    const colNames = this._sourceData.columns.map((c) => c.name);
    const mappingResult = validateMappingConfig(this._mappingConfig, colNames);
    if (!mappingResult.valid) {
      return this._fail("validate_mapping", `Invalid mapping: ${mappingResult.errors.join("; ")}`);
    }

    // Step 2: Validate user params
    this._markStep("validate_params");
    const paramsResult = validateUserParams(this._userParams);
    if (!paramsResult.valid) {
      return this._fail("validate_params", `Invalid params: ${paramsResult.errors.join("; ")}`);
    }

    // Step 3: Validate DC values
    this._markStep("validate_dc");
    const dcResult = validateDCValues(this._sourceData, this._mappingConfig.dcColumn);
    if (!dcResult.valid) {
      return this._fail("validate_dc", `DC validation failed: ${dcResult.errors.join("; ")}`);
    }

    // Step 4: Fetch template (if not already set)
    this._markStep("fetch_template");
    if (!this._template) {
      return this._fail("fetch_template", "No template selected. Call selectTemplate() first.");
    }

    // Step 5: Generate SQL
    this._markStep("sql_generation");
    let sql: string;
    try {
      sql = generateTransformSql(this._mappingConfig, this._template, this._userParams);
    } catch (err) {
      const msg = err instanceof SQLGenerationError ? err.message : String(err);
      return this._fail("sql_generation", `SQL generation failed: ${msg}`);
    }
    this._generatedSql = sql;

    // Step 6: Execute in DuckDB-WASM
    this._markStep("duckdb_execute");
    try {
      await duckdb.initialize();
      await duckdb.registerTable(this._sourceData, "budget");
      const result = await duckdb.executeSql(sql);
      this._transformResult = result;
      return { ok: true, data: result };
    } catch (err) {
      return this._fail("duckdb_execute", `DuckDB execution failed: ${(err as Error).message}`);
    }
  }

  /** Release the pending workbook without proceeding. Safe to call anytime. */
  cancelPendingImport(): void {
    this._pendingWorkbook = null;
    this._pendingSheetName = null;
  }

  /** Reset all session state. */
  reset(): void {
    this._pendingWorkbook = null;
    this._pendingSheetName = null;
    this._sourceData = null;
    this._financialDocument = null;
    this._mappingConfig = null;
    this._template = null;
    this._userParams = null;
    this._transformResult = null;
    this._generatedSql = null;
    this._resetTrace();
  }

  // --- Internal helpers ---

  /**
   * Scan for header row and either auto-extract or return HeaderSelectionNeeded.
   * Shared logic for importFile (Budget sheet) and importWithSheet.
   */
  private _resolveHeaderRow(workbook: XLSX.WorkBook, sheetName: string): ImportResult {
    const scanResult = scanForHeaderRow(workbook, sheetName);
    if (scanResult instanceof ParseError) {
      return this._fail("extract_data", scanResult.message);
    }

    const { candidateRows, rawPreview } = scanResult;

    // Row 0 is a candidate → auto-select row 0
    if (candidateRows.includes(0)) {
      return this._extractWithHeaderRow(workbook, sheetName, 0);
    }

    // Exactly one candidate (not row 0) → auto-select
    if (candidateRows.length === 1) {
      return this._extractWithHeaderRow(workbook, sheetName, candidateRows[0]);
    }

    // Zero or multiple candidates → prompt user
    this._pendingWorkbook = workbook;
    this._pendingSheetName = sheetName;
    return { needsHeaderSelection: true, candidateRows, rawPreview };
  }

  /**
   * Extract budget data and mapping config using a specific header row index.
   * On success, stores data/mapping and clears pending state.
   * On failure, keeps pending state so user can retry.
   */
  private _extractWithHeaderRow(
    workbook: XLSX.WorkBook,
    sheetName: string,
    headerRowIndex: number,
  ): Result<TabularData> {
    this._markStep("extract_data");
    const data = extractBudgetData(workbook, sheetName, headerRowIndex);
    if (data instanceof ParseError) {
      return this._fail("extract_data", data.message);
    }

    this._markStep("extract_mapping");
    const mapping = extractMappingConfig(workbook, sheetName, headerRowIndex);
    if (mapping instanceof MappingError) {
      return this._fail("extract_mapping", mapping.message);
    }

    this._sourceData = data;
    this._mappingConfig = mapping;

    // Produce FinancialDocument as the canonical inter-stage representation
    try {
      this._financialDocument = tabularBudgetToFinancialDocument(data, mapping, sheetName);
    } catch {
      // Non-fatal: FinancialDocument production is best-effort during migration
      this._financialDocument = null;
    }

    this._pendingWorkbook = null;
    this._pendingSheetName = null;
    return { ok: true, data };
  }

  private _resetTrace(): void {
    this._trace = { executedSteps: [], failedStep: null };
  }

  private _markStep(step: PipelineStep): void {
    this._trace.executedSteps.push(step);
  }

  private _fail(step: PipelineStep, message: string): Result<never> {
    this._trace.failedStep = step;
    return { ok: false, error: `[${step}] ${message}` };
  }
}
