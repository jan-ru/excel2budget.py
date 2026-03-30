/**
 * Client-side CSV and Excel export for transformed tabular data.
 *
 * Generates downloadable files entirely in the browser — no data is
 * transmitted to any server.
 *
 * Requirements: 11.1, 11.2, 11.5
 */

import type { components } from "../types/api";
import type { FinancialDocument, FinancialLine } from "../types/domain";

type TabularData = components["schemas"]["TabularData"];
type CellValue = components["schemas"]["Row"]["values"][number];

/** Column headers for FinancialDocument CSV/Excel export. */
const FD_COLUMNS = ["account", "entity", "period", "amount", "line_type", "currency", "memo"] as const;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Convert a discriminated CellValue union to its string representation. */
export function cellValueToString(cell: CellValue): string {
  switch (cell.type) {
    case "string":
      return cell.value;
    case "int":
    case "float":
      return String(cell.value);
    case "bool":
      return cell.value ? "true" : "false";
    case "date":
      return cell.value;
    case "null":
      return "";
  }
}

/**
 * Escape a value for CSV: wrap in double-quotes if it contains a comma,
 * double-quote, or newline. Internal double-quotes are doubled.
 */
function csvEscape(value: string): string {
  if (
    value.includes(",") ||
    value.includes('"') ||
    value.includes("\n") ||
    value.includes("\r")
  ) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

// ---------------------------------------------------------------------------
// CSV Export
// ---------------------------------------------------------------------------

/** Build a CSV string from TabularData. @deprecated Use financialDocumentToCsv instead. */
export function tabularDataToCsv(data: TabularData): string {
  const header = data.columns.map((c) => csvEscape(c.name)).join(",");
  const rows = data.rows.map((row) =>
    row.values.map((v) => csvEscape(cellValueToString(v))).join(","),
  );
  return [header, ...rows].join("\n");
}

/** Trigger a browser download of a CSV string. */
function downloadCsvString(csv: string, filename: string): void {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  triggerDownload(blob, filename);
}

/** Trigger a browser download of an Excel file from a 2D string array. */
async function downloadAoaAsExcel(aoa: string[][], filename: string): Promise<void> {
  const XLSX = await import("xlsx");
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
  const buf: ArrayBuffer = XLSX.write(wb, {
    bookType: "xlsx",
    type: "array",
  });
  const blob = new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  triggerDownload(blob, filename);
}

/** Trigger a browser download of a CSV file. @deprecated Use downloadFinancialDocumentCsv instead. */
export function downloadCsv(
  data: TabularData,
  filename: string = "export.csv",
): void {
  downloadCsvString(tabularDataToCsv(data), filename);
}

// ---------------------------------------------------------------------------
// Excel Export (SheetJS / xlsx)
// ---------------------------------------------------------------------------

/** Build a SheetJS-compatible 2D array from TabularData. @deprecated Use financialDocumentToAoa instead. */
export function tabularDataToAoa(data: TabularData): string[][] {
  const header = data.columns.map((c) => c.name);
  const rows = data.rows.map((row) => row.values.map(cellValueToString));
  return [header, ...rows];
}

/** Trigger a browser download of an Excel (.xlsx) file. @deprecated Use downloadFinancialDocumentExcel instead. */
export async function downloadExcel(
  data: TabularData,
  filename: string = "export.xlsx",
): Promise<void> {
  await downloadAoaAsExcel(tabularDataToAoa(data), filename);
}

// ---------------------------------------------------------------------------
// FinancialDocument CSV Export
// ---------------------------------------------------------------------------

/** Convert a FinancialLine field value to string. */
function lineFieldToString(line: FinancialLine, field: typeof FD_COLUMNS[number]): string {
  const val = line[field];
  if (val === null || val === undefined) return "";
  return String(val);
}

/** Build a CSV string from a FinancialDocument (one row per FinancialLine). */
export function financialDocumentToCsv(doc: FinancialDocument): string {
  const header = FD_COLUMNS.map((c) => csvEscape(c)).join(",");
  const rows = doc.lines.map((line) =>
    FD_COLUMNS.map((col) => csvEscape(lineFieldToString(line, col))).join(","),
  );
  return [header, ...rows].join("\n");
}

/** Build a SheetJS-compatible 2D array from a FinancialDocument. */
export function financialDocumentToAoa(doc: FinancialDocument): string[][] {
  const header = [...FD_COLUMNS];
  const rows = doc.lines.map((line) =>
    FD_COLUMNS.map((col) => lineFieldToString(line, col)),
  );
  return [header, ...rows];
}

/** Trigger a browser download of a CSV file from a FinancialDocument. */
export function downloadFinancialDocumentCsv(
  doc: FinancialDocument,
  filename: string = "export.csv",
): void {
  downloadCsvString(financialDocumentToCsv(doc), filename);
}

/** Trigger a browser download of an Excel file from a FinancialDocument. */
export async function downloadFinancialDocumentExcel(
  doc: FinancialDocument,
  filename: string = "export.xlsx",
): Promise<void> {
  await downloadAoaAsExcel(financialDocumentToAoa(doc), filename);
}

// ---------------------------------------------------------------------------
// Shared download helper
// ---------------------------------------------------------------------------

/** Create a temporary <a> element to trigger a file download. */
function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
