/**
 * Header row selector component for choosing which row contains column headers.
 * Requirements: 3.2, 3.3, 3.4, 3.5, 3.6
 */

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
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Header row selection");
  select.style.cssText =
    "padding:6px 10px;border:1px solid #d1d5db;border-radius:4px;font-size:14px;min-width:200px;";

  const placeholder = document.createElement("option");
  placeholder.textContent = "Select a header row\u2026";
  placeholder.value = "";
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  for (const idx of indices) {
    const opt = document.createElement("option");
    opt.value = String(idx);
    const row = idx < rawPreview.length ? rawPreview[idx] : [];
    const preview = Array.isArray(row) ? previewCells(row) : "";
    opt.textContent = `Row ${idx + 1}: ${preview}`;
    select.appendChild(opt);
  }

  // Button row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;";

  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.disabled = true;
  confirmBtn.setAttribute("aria-label", "Confirm header row selection");
  confirmBtn.style.cssText =
    "padding:6px 14px;border:1px solid #d1d5db;border-radius:4px;background:#2563eb;color:#fff;cursor:pointer;font-size:13px;";

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.setAttribute("aria-label", "Cancel header row selection");
  cancelBtn.style.cssText =
    "padding:6px 14px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;font-size:13px;";

  // Enable confirm when a real row is selected
  select.addEventListener("change", () => {
    confirmBtn.disabled = select.value === "";
  });

  confirmBtn.addEventListener("click", () => {
    if (select.value !== "") {
      onConfirm(Number(select.value));
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
