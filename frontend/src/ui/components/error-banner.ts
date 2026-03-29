/**
 * Error banner component for displaying error messages.
 * Requirements: 14.2
 */

/** Render an error banner into the given container. Clears previous content. */
export function showError(container: HTMLElement, message: string): void {
  container.innerHTML = "";
  const banner = document.createElement("div");
  banner.setAttribute("role", "alert");
  banner.style.cssText =
    "padding:12px 16px;background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;color:#991b1b;margin:8px 0;font-size:14px;";
  banner.textContent = message;
  container.appendChild(banner);
}

/** Clear the error banner. */
export function clearError(container: HTMLElement): void {
  container.innerHTML = "";
}
