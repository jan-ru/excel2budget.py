/**
 * Pre-transform validation for imported budget data.
 *
 * Validates MappingConfig column references, UserParams constraints,
 * DC column values, and month column period numbers before transformation.
 * All processing happens in the browser — no data is sent to any server.
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4
 */

import type { components } from "../types/api";

// --- Type aliases from generated API types ---
type MappingConfig = components["schemas"]["MappingConfig"];
type TabularData = components["schemas"]["TabularData"];
type UserParams = components["schemas"]["UserParams"];
type ValidationResult = components["schemas"]["ValidationResult"];
type CellValue = components["schemas"]["Row"]["values"][number];

// --- Public API ---

/**
 * Validate that MappingConfig column references exist in the provided column
 * names, and that month column period numbers are unique and in range 1–12.
 */
export function validateMappingConfig(
  config: MappingConfig,
  columnNames: string[],
): ValidationResult {
  const errors: string[] = [];
  const colSet = new Set(columnNames);

  // Referenced columns must exist
  for (const [refName, label] of [
    [config.entityColumn, "entityColumn"],
    [config.accountColumn, "accountColumn"],
    [config.dcColumn, "dcColumn"],
  ] as const) {
    if (!colSet.has(refName)) {
      errors.push(`${label} '${refName}' not found in columns`);
    }
  }

  for (const mc of config.monthColumns) {
    if (!colSet.has(mc.sourceColumnName)) {
      errors.push(`Month column '${mc.sourceColumnName}' not found in columns`);
    }
  }

  // Month columns count
  const mcCount = config.monthColumns.length;
  if (mcCount < 1 || mcCount > 12) {
    errors.push(`monthColumns count must be 1–12, got ${mcCount}`);
  }

  // Period number range and uniqueness
  const seenPeriods: number[] = [];
  for (const mc of config.monthColumns) {
    if (mc.periodNumber < 1 || mc.periodNumber > 12) {
      errors.push(
        `periodNumber ${mc.periodNumber} for column '${mc.sourceColumnName}' is out of range 1–12`,
      );
    }
    if (seenPeriods.includes(mc.periodNumber)) {
      errors.push(
        `Duplicate periodNumber ${mc.periodNumber} for column '${mc.sourceColumnName}'`,
      );
    }
    seenPeriods.push(mc.periodNumber);
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validate UserParams: budgetcode must be non-empty (after trimming),
 * year must be positive.
 */
export function validateUserParams(params: UserParams): ValidationResult {
  const errors: string[] = [];

  if (!params.budgetcode || params.budgetcode.trim() === "") {
    errors.push("budgetcode must be non-empty");
  }

  if (params.year <= 0) {
    errors.push(`year must be positive, got ${params.year}`);
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Detect rows with invalid DC values. Valid values are "D", "C", or null.
 * Returns an error entry for every invalid row, including the row index
 * and the offending value.
 */
export function validateDCValues(
  data: TabularData,
  dcColumnName: string,
): ValidationResult {
  const errors: string[] = [];

  const dcIndex = data.columns.findIndex((c) => c.name === dcColumnName);
  if (dcIndex === -1) {
    errors.push(`DC column '${dcColumnName}' not found in data`);
    return { valid: false, errors };
  }

  for (let i = 0; i < data.rows.length; i++) {
    const cell = data.rows[i].values[dcIndex];
    if (!isValidDC(cell)) {
      const display = cellDisplayValue(cell);
      errors.push(`Row ${i}: invalid DC value '${display}'`);
    }
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Validate TabularData structural invariants: row length consistency,
 * column name uniqueness, and rowCount accuracy.
 */
export function validateTabularData(data: TabularData): ValidationResult {
  const errors: string[] = [];
  const colCount = data.columns.length;

  // Column name uniqueness
  const seen = new Set<string>();
  for (const col of data.columns) {
    if (seen.has(col.name)) {
      errors.push(`Duplicate column name: '${col.name}'`);
    }
    seen.add(col.name);
  }

  // rowCount consistency
  if (data.rowCount !== data.rows.length) {
    errors.push(
      `rowCount mismatch: declared ${data.rowCount}, actual ${data.rows.length}`,
    );
  }

  // Row length matches column count
  for (let i = 0; i < data.rows.length; i++) {
    if (data.rows[i].values.length !== colCount) {
      errors.push(
        `Row ${i} has ${data.rows[i].values.length} values, expected ${colCount}`,
      );
    }
  }

  return { valid: errors.length === 0, errors };
}

// --- Internal helpers ---

function isValidDC(cell: CellValue): boolean {
  if (cell.type === "null") return true;
  if (cell.type === "string") {
    return cell.value === "D" || cell.value === "C";
  }
  return false;
}

function cellDisplayValue(cell: CellValue): string {
  if (cell.type === "null") return "null";
  return String((cell as { value: unknown }).value);
}
