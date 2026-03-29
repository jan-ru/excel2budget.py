/**
 * IronCalc-WASM engine wrapper for in-browser spreadsheet rendering.
 *
 * Wraps @ironcalc/wasm to load TabularData into a spreadsheet model
 * and render it into a DOM element. All cell values are sanitized
 * via XSS_Sanitizer before rendering.
 *
 * Requirements: 10.1, 10.2
 */

import type { Model as IronCalcModel } from "@ironcalc/wasm";
import type { components } from "../types/api";
import { sanitizeCellValue } from "../security/xss-sanitizer";

// --- Type aliases from generated API types ---
type TabularData = components["schemas"]["TabularData"];
type CellValue = components["schemas"]["Row"]["values"][number];

// --- Error types ---

export class IronCalcEngineError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "IronCalcEngineError";
  }
}

// --- Lazy-loaded IronCalc module ---

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let ModelCtor: (new (...args: any[]) => IronCalcModel) | null = null;
let initPromise: Promise<void> | null = null;

/**
 * Ensure the IronCalc WASM module is initialized.
 */
async function ensureInit(): Promise<void> {
  if (ModelCtor) return;
  if (!initPromise) {
    initPromise = (async () => {
      const mod = await import("@ironcalc/wasm");
      await mod.default();
      ModelCtor = mod.Model;
    })();
  }
  await initPromise;
}

// --- Internal helpers ---

/** Convert a CellValue to a plain string for IronCalc's setUserInput. */
function cellToInputString(cell: CellValue): string {
  switch (cell.type) {
    case "string":
      return cell.value;
    case "int":
      return String(cell.value);
    case "float":
      return String(cell.value);
    case "bool":
      return cell.value ? "TRUE" : "FALSE";
    case "date":
      return cell.value;
    case "null":
      return "";
  }
}

// --- Handle types ---

/** Opaque handle wrapping an IronCalc Model instance and its sheet metadata. */
export interface SheetHandle {
  _model: IronCalcModel;
  sheetIndex: number;
  sheetName: string;
  totalRows: number;
  totalCols: number;
}

// --- Public API ---

/**
 * Load TabularData into a new IronCalc workbook.
 *
 * Creates a Model, writes column headers into row 1 and data rows
 * starting at row 2. All string cell values are sanitized via
 * XSS_Sanitizer before being written to the model.
 *
 * @param data - The tabular data to load.
 * @param sheetName - Name for the sheet (default "Sheet1").
 * @returns A SheetHandle for the populated sheet.
 */
export async function loadData(
  data: TabularData,
  sheetName: string = "Sheet1",
): Promise<SheetHandle> {
  await ensureInit();
  const model = new ModelCtor!("workbook", "en", "UTC", "en");
  const sheetIdx = 0;

  // Write header row (IronCalc uses 1-based indexing)
  for (let c = 0; c < data.columns.length; c++) {
    const name = sanitizeCellValue(data.columns[c].name);
    model.setUserInput(sheetIdx, 1, c + 1, name);
  }

  // Write data rows starting at row 2
  for (let r = 0; r < data.rows.length; r++) {
    const row = data.rows[r];
    for (let c = 0; c < row.values.length; c++) {
      const cell = row.values[c];
      let input = cellToInputString(cell);
      if (cell.type === "string") {
        input = sanitizeCellValue(input);
      }
      if (input !== "") {
        model.setUserInput(sheetIdx, r + 2, c + 1, input);
      }
    }
  }

  return {
    _model: model,
    sheetIndex: sheetIdx,
    sheetName,
    totalRows: data.rows.length + 1, // header + data
    totalCols: data.columns.length,
  };
}

/**
 * Render a SheetHandle's data into a DOM element as an HTML table.
 *
 * Reads all cells from the IronCalc model using getFormattedCellValue,
 * sanitizes each value, and builds a <table> element mounted into the
 * target container.
 *
 * @param handle - The SheetHandle returned by loadData.
 * @param container - The DOM element to mount the spreadsheet view into.
 */
export function renderToElement(
  handle: SheetHandle,
  container: HTMLElement,
): void {
  if (!handle._model) {
    throw new IronCalcEngineError(
      "Invalid SheetHandle: model is not available.",
    );
  }

  const { _model: model, sheetIndex, totalRows, totalCols } = handle;

  if (totalCols === 0) {
    container.innerHTML = "<p>No data to display.</p>";
    return;
  }

  const table = document.createElement("table");
  table.setAttribute("role", "grid");
  table.style.borderCollapse = "collapse";
  table.style.width = "100%";
  table.style.fontFamily = "monospace";
  table.style.fontSize = "13px";

  // Header row (row 1 in IronCalc, 1-based)
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (let c = 1; c <= totalCols; c++) {
    const th = document.createElement("th");
    th.setAttribute("scope", "col");
    const raw = model.getFormattedCellValue(sheetIndex, 1, c);
    th.textContent = sanitizeCellValue(raw);
    th.style.border = "1px solid #ccc";
    th.style.padding = "4px 8px";
    th.style.backgroundColor = "#f5f5f5";
    th.style.textAlign = "left";
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Data rows (row 2 onward)
  const tbody = document.createElement("tbody");
  for (let r = 2; r <= totalRows; r++) {
    const tr = document.createElement("tr");
    for (let c = 1; c <= totalCols; c++) {
      const td = document.createElement("td");
      const raw = model.getFormattedCellValue(sheetIndex, r, c);
      td.textContent = sanitizeCellValue(raw);
      td.style.border = "1px solid #eee";
      td.style.padding = "4px 8px";
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  container.innerHTML = "";
  container.appendChild(table);
}

/**
 * Read a single formatted cell value from the model (sanitized).
 *
 * @param handle - The SheetHandle to read from.
 * @param row - 1-based row index.
 * @param col - 1-based column index.
 * @returns The sanitized display string.
 */
export function getCellValue(
  handle: SheetHandle,
  row: number,
  col: number,
): string {
  if (!handle._model) {
    throw new IronCalcEngineError(
      "Invalid SheetHandle: model is not available.",
    );
  }
  const raw = handle._model.getFormattedCellValue(
    handle.sheetIndex,
    row,
    col,
  );
  return sanitizeCellValue(raw);
}
