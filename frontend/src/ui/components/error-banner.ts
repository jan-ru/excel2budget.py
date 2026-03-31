/**
 * Error banner component for displaying error messages.
 * Requirements: 3.1, 3.2, 3.3, 3.4, 11.1
 */

import "@ui5/webcomponents/dist/MessageStrip.js";

/** Render an error banner into the given container. Clears previous content. */
export function showError(container: HTMLElement, message: string): void {
  container.innerHTML = "";
  const banner = document.createElement("ui5-message-strip");
  banner.setAttribute("design", "Negative");
  banner.setAttribute("role", "alert");
  banner.textContent = message;
  container.appendChild(banner);
}

/** Clear the error banner. */
export function clearError(container: HTMLElement): void {
  container.innerHTML = "";
}
