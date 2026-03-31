/**
 * Generic selector panel: ui5-select with options + Confirm/Cancel buttons.
 * Shared by sheet-selector and header-row-selector to avoid duplication.
 */

import "@ui5/webcomponents/dist/Select.js";
import "@ui5/webcomponents/dist/Option.js";
import "@ui5/webcomponents/dist/Button.js";

/** A single option to display in the selector dropdown. */
export interface SelectorOption {
  value: string;
  label: string;
}

/** Configuration for the generic selector panel. */
export interface SelectorPanelConfig {
  ariaLabel: string;
  placeholderText: string;
  options: SelectorOption[];
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

/**
 * Create a selector panel with a ui5-select dropdown and Confirm/Cancel buttons.
 * Returns the root container element.
 */
export function createSelectorPanel(config: SelectorPanelConfig): HTMLElement {
  const { ariaLabel, placeholderText, options, onConfirm, onCancel } = config;

  const container = document.createElement("div");
  container.style.cssText =
    "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px;";

  // Dropdown
  const select = document.createElement("ui5-select");
  select.setAttribute("aria-label", ariaLabel);

  const placeholder = document.createElement("ui5-option");
  placeholder.textContent = placeholderText;
  placeholder.setAttribute("value", "");
  placeholder.setAttribute("disabled", "");
  placeholder.setAttribute("selected", "");
  select.appendChild(placeholder);

  for (const opt of options) {
    const el = document.createElement("ui5-option");
    el.setAttribute("value", opt.value);
    el.textContent = opt.label;
    select.appendChild(el);
  }

  // Button row
  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:8px;";

  const confirmBtn = document.createElement("ui5-button");
  confirmBtn.textContent = "Confirm";
  confirmBtn.setAttribute("disabled", "");
  confirmBtn.setAttribute("aria-label", `Confirm ${ariaLabel.toLowerCase()}`);
  confirmBtn.setAttribute("design", "Emphasized");

  const cancelBtn = document.createElement("ui5-button");
  cancelBtn.textContent = "Cancel";
  cancelBtn.setAttribute("aria-label", `Cancel ${ariaLabel.toLowerCase()}`);
  cancelBtn.setAttribute("design", "Transparent");

  // Enable confirm when a real option is selected
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
