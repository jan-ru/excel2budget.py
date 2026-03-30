/**
 * Sheet selector component for choosing a sheet from a workbook.
 * Requirements: 3.2, 3.3, 3.4, 3.5
 */

/** Options for creating a sheet selector component. */
export interface SheetSelectorOptions {
  sheetNames: string[];
  onConfirm: (sheetName: string) => void;
  onCancel: () => void;
}

/**
 * Render a sheet selection dropdown with Confirm/Cancel actions.
 * Returns the root element for insertion into the DOM.
 */
export function createSheetSelector(options: SheetSelectorOptions): HTMLElement {
  const { sheetNames, onConfirm, onCancel } = options;

  const container = document.createElement("div");
  container.style.cssText =
    "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px;";

  // Dropdown
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Sheet selection");
  select.style.cssText =
    "padding:6px 10px;border:1px solid #d1d5db;border-radius:4px;font-size:14px;min-width:200px;";

  const placeholder = document.createElement("option");
  placeholder.textContent = "Select a sheet\u2026";
  placeholder.value = "";
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  for (const name of sheetNames) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  }

  // Button row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;";

  const confirmBtn = document.createElement("button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.disabled = true;
  confirmBtn.setAttribute("aria-label", "Confirm sheet selection");
  confirmBtn.style.cssText =
    "padding:6px 14px;border:1px solid #d1d5db;border-radius:4px;background:#2563eb;color:#fff;cursor:pointer;font-size:13px;";

  const cancelBtn = document.createElement("button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.setAttribute("aria-label", "Cancel sheet selection");
  cancelBtn.style.cssText =
    "padding:6px 14px;border:1px solid #d1d5db;border-radius:4px;background:#fff;cursor:pointer;font-size:13px;";

  // Enable confirm when a real sheet is selected
  select.addEventListener("change", () => {
    confirmBtn.disabled = select.value === "";
  });

  confirmBtn.addEventListener("click", () => {
    if (select.value) {
      onConfirm(select.value);
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
