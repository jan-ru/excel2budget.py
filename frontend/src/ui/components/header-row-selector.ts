/**
 * Header row selector component for choosing which row contains column headers.
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 11.1
 */

import "@ui5/webcomponents/dist/Select.js";
import "@ui5/webcomponents/dist/Option.js";
import "@ui5/webcomponents/dist/Button.js";

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

  const container = document.createElement("div");
  container.style.cssText =
    "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px;";

  // Determine which row indices to show
  const indices =
    candidateRows.length > 0
      ? candidateRows
      : Array.from(
          { length: Math.min(20, rawPreview.length) },
          (_, i) => i,
        );

  // Dropdown
  const select = document.createElement("ui5-select");
  select.setAttribute("aria-label", "Header row selection");

  const placeholder = document.createElement("ui5-option");
  placeholder.textContent = "Select a header row\u2026";
  placeholder.setAttribute("value", "");
  placeholder.setAttribute("disabled", "");
  placeholder.setAttribute("selected", "");
  select.appendChild(placeholder);

  for (const idx of indices) {
    const opt = document.createElement("ui5-option");
    opt.setAttribute("value", String(idx));
    const row = idx < rawPreview.length ? rawPreview[idx] : [];
    const preview = Array.isArray(row) ? previewCells(row) : "";
    opt.textContent = `Row ${idx + 1}: ${preview}`;
    select.appendChild(opt);
  }

  // Button row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;";

  const confirmBtn = document.createElement("ui5-button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.setAttribute("disabled", "");
  confirmBtn.setAttribute("aria-label", "Confirm header row selection");
  confirmBtn.setAttribute("design", "Emphasized");

  const cancelBtn = document.createElement("ui5-button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.setAttribute("aria-label", "Cancel header row selection");
  cancelBtn.setAttribute("design", "Transparent");

  // Enable confirm when a real row is selected
  select.addEventListener("change", (e: Event) => {
    const selectedOption = (e as CustomEvent).detail?.selectedOption;
    const value = selectedOption?.getAttribute?.("value") ?? selectedOption?.value ?? "";
    if (value) {
      confirmBtn.removeAttribute("disabled");
    } else {
      confirmBtn.setAttribute("disabled", "");
    }
  });

  confirmBtn.addEventListener("click", () => {
    const selectedOpt = select.querySelector("ui5-option[selected]:not([disabled])") as HTMLElement | null;
    const value = selectedOpt?.getAttribute("value") ?? "";
    if (value !== "") {
      onConfirm(Number(value));
    }
  });

  cancelBtn.addEventListener("click", () => {
    onCancel();
  });

  btnRow.appendChild(confirmBtn);
  btnRow.appendChild(cancelBtn);

  container.appendChild(select);
  container.appendChild(btnRow);

  return container;
}
