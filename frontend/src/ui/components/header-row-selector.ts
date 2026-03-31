/**
 * Header row selector component for choosing which row contains column headers.
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 11.1
 */

import { createSelectorPanel } from "./selector-panel";

/** Options for creating a header row selector component. */
export interface HeaderRowSelectorOptions {
  /** Zero-based candidate row indices. If empty, all rows 0–19 are offered. */
  candidateRows: number[];
  /** Raw sheet data rows for preview display. */
  rawPreview: unknown[][];
  onConfirm: (headerRowIndex: number) => void;
  onCancel: () => void;
}

/** Format the first 3 cell values of a row for display. */
function previewCells(row: unknown[]): string {
  return row
    .slice(0, 3)
    .map((c) => (c == null ? "" : String(c).trim()))
    .join(", ");
}

/**
 * Render a header row selection dropdown with row previews.
 * Each option shows the 1-based row number and the first 3 cell values.
 * Returns the root element for insertion into the DOM.
 */
export function createHeaderRowSelector(
  options: HeaderRowSelectorOptions,
): HTMLElement {
  const { candidateRows, rawPreview, onConfirm, onCancel } = options;

  // Determine which row indices to show
  const indices =
    candidateRows.length > 0
      ? candidateRows
      : Array.from(
          { length: Math.min(20, rawPreview.length) },
          (_, i) => i,
        );

  return createSelectorPanel({
    ariaLabel: "Header row selection",
    placeholderText: "Select a header row\u2026",
    options: indices.map((idx) => {
      const row = idx < rawPreview.length ? rawPreview[idx] : [];
      const preview = Array.isArray(row) ? previewCells(row) : "";
      return { value: String(idx), label: `Row ${idx + 1}: ${preview}` };
    }),
    onConfirm: (value) => onConfirm(Number(value)),
    onCancel,
  });
}
