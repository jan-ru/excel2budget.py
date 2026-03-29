/**
 * Client-side CSV and Excel export for transformed tabular data.
 *
 * Generates downloadable files entirely in the browser — no data is
 * transmitted to any server.
 *
 * Requirements: 11.1, 11.2, 11.5
 */

import type { components } from "../types/api";

type TabularData = components["schemas"]["TabularData"];
type CellValue = components["schemas"]["Row"]["values"][number];

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

/** Build a CSV string from TabularData. */
export function tabularDataToCsv(data: TabularData): string {
  const header = data.columns.map((c) => csvEscape(c.name)).join(",");
  const rows = data.rows.map((row) =>
    row.values.map((v) => csvEscape(cellValueToString(v))).join(","),
  );
  return [header, ...rows].join("\n");
}

/** Trigger a browser download of a CSV file. */
export function downloadCsv(
  data: TabularData,
  filename: string = "export.csv",
): void {
  const csv = tabularDataToCsv(data);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  triggerDownload(blob, filename);
}

// ---------------------------------------------------------------------------
// Excel Export (SheetJS / xlsx)
// ---------------------------------------------------------------------------

/** Build a SheetJS-compatible 2D array from TabularData. */
export function tabularDataToAoa(data: TabularData): string[][] {
  const header = data.columns.map((c) => c.name);
  const rows = data.rows.map((row) => row.values.map(cellValueToString));
  return [header, ...rows];
}

/** Trigger a browser download of an Excel (.xlsx) file. */
export async function downloadExcel(
  data: TabularData,
  filename: string = "export.xlsx",
): Promise<void> {
  const XLSX = await import("xlsx");
  const aoa = tabularDataToAoa(data);
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
