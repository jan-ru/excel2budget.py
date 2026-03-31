/**
 * Sheet selector component for choosing a sheet from a workbook.
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 11.1
 */

import { createSelectorPanel } from "./selector-panel";

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

  return createSelectorPanel({
    ariaLabel: "Sheet selection",
    placeholderText: "Select a sheet\u2026",
    options: sheetNames.map((name) => ({ value: name, label: name })),
    onConfirm,
    onCancel,
  });
}
