/**
 * Minimal stub for UI5 custom elements in jsdom.
 * Registers stub custom elements so document.createElement("ui5-*") returns
 * elements with the expected tag names and attribute support.
 */

const registered = new Set<string>();

/** Register a stub custom element for the given tag name if not already registered. */
export function registerUI5Stub(tagName: string): void {
  if (registered.has(tagName)) return;
  if (typeof customElements === "undefined") return;
  try {
    if (customElements.get(tagName)) {
      registered.add(tagName);
      return;
    }
    customElements.define(tagName, class extends HTMLElement {});
    registered.add(tagName);
  } catch {
    // Already defined or invalid — ignore
  }
}

/** Register all UI5 stubs used across the migration. */
export function registerAllUI5Stubs(): void {
  const tags = [
    "ui5-message-strip",
    "ui5-button",
    "ui5-select",
    "ui5-option",
    "ui5-input",
    "ui5-label",
    "ui5-file-uploader",
    "ui5-tabcontainer",
    "ui5-tab",
  ];
  for (const tag of tags) {
    registerUI5Stub(tag);
  }
}
