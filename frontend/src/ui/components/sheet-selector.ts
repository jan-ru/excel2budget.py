/**
 * Sheet selector component for choosing a sheet from a workbook.
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 11.1
 */

import "@ui5/webcomponents/dist/Select.js";
import "@ui5/webcomponents/dist/Option.js";
import "@ui5/webcomponents/dist/Button.js";

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
  const select = document.createElement("ui5-select");
  select.setAttribute("aria-label", "Sheet selection");

  const placeholder = document.createElement("ui5-option");
  placeholder.textContent = "Select a sheet\u2026";
  placeholder.setAttribute("value", "");
  placeholder.setAttribute("disabled", "");
  placeholder.setAttribute("selected", "");
  select.appendChild(placeholder);

  for (const name of sheetNames) {
    const opt = document.createElement("ui5-option");
    opt.setAttribute("value", name);
    opt.textContent = name;
    select.appendChild(opt);
  }

  // Button row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;";

  const confirmBtn = document.createElement("ui5-button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.setAttribute("disabled", "");
  confirmBtn.setAttribute("aria-label", "Confirm sheet selection");
  confirmBtn.setAttribute("design", "Emphasized");

  const cancelBtn = document.createElement("ui5-button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.setAttribute("aria-label", "Cancel sheet selection");
  cancelBtn.setAttribute("design", "Transparent");

  // Enable confirm when a real sheet is selected
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
    // Read the currently selected option's value
    const selectedOpt = select.querySelector("ui5-option[selected]:not([disabled])") as HTMLElement | null;
    const value = selectedOpt?.getAttribute("value") ?? "";
    if (value) {
      onConfirm(value);
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
