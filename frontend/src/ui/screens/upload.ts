/**
 * Upload screen: file input accepting .xlsx, triggers Pipeline_Orchestrator.importFile.
 * Shows error banner on failure.
 * Requirements: 7.1, 14.1
 */

import type { ScreenContext } from "../app";
import { showError, clearError } from "../components/error-banner";

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator, navigate } = ctx;

  const wrapper = document.createElement("div");
  wrapper.style.cssText = "max-width:480px;margin:40px auto;text-align:center;";

  const heading = document.createElement("h2");
  heading.textContent = "Upload Budget File";
  heading.style.cssText = "margin-bottom:16px;font-size:20px;font-weight:600;";

  const desc = document.createElement("p");
  desc.textContent = "Select an Excel (.xlsx) budget file to begin.";
  desc.style.cssText = "color:#6b7280;margin-bottom:24px;font-size:14px;";

  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".xlsx";
  input.setAttribute("aria-label", "Upload Excel file");
  input.style.cssText = "margin-bottom:16px;";

  const status = document.createElement("p");
  status.style.cssText = "font-size:14px;color:#374151;";

  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;

    clearError(errorEl);
    status.textContent = "Importing…";

    const result = await orchestrator.importFile(file);
    if (!result.ok) {
      status.textContent = "";
      showError(errorEl, result.error);
      return;
    }

    const data = result.data;
    status.textContent = `Imported ${data.rowCount} rows, ${data.columns.length} columns.`;
    // Auto-navigate to preview after short delay
    setTimeout(() => navigate("preview"), 600);
  });

  wrapper.appendChild(heading);
  wrapper.appendChild(desc);
  wrapper.appendChild(input);
  wrapper.appendChild(status);
  contentEl.appendChild(wrapper);
}
