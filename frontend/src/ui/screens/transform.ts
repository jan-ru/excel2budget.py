/**
 * Transform screen: trigger transformation via Pipeline_Orchestrator.runTransform.
 * Display success/error result.
 * Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 13.3
 */

import "@ui5/webcomponents/dist/Button.js";

import type { ScreenContext } from "../app";
import { showError, clearError } from "../components/error-banner";

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator, navigate } = ctx;

  const wrapper = document.createElement("div");
  wrapper.style.cssText = "max-width:480px;margin:40px auto;text-align:center;";

  const heading = document.createElement("h2");
  heading.textContent = "Transform Data";
  heading.style.cssText = "margin-bottom:16px;font-size:20px;font-weight:600;";

  const info = document.createElement("p");
  info.style.cssText = "color:#6b7280;font-size:14px;margin-bottom:24px;";

  if (!orchestrator.sourceData) {
    info.textContent = "No data imported. Please upload a file first.";
  } else if (!orchestrator.template || !orchestrator.userParams) {
    info.textContent = "Please configure package, template, and parameters first.";
  } else {
    info.textContent =
      `Ready to transform ${orchestrator.sourceData.rowCount} rows ` +
      `using ${orchestrator.template.packageName}/${orchestrator.template.templateName}.`;
  }

  const runBtn = document.createElement("ui5-button");
  runBtn.textContent = "Run Transformation";
  runBtn.setAttribute("design", "Emphasized");
  if (!orchestrator.sourceData || !orchestrator.template || !orchestrator.userParams) {
    runBtn.setAttribute("disabled", "");
  }

  const status = document.createElement("p");
  status.style.cssText = "margin-top:16px;font-size:14px;";

  runBtn.addEventListener("click", async () => {
    clearError(errorEl);
    runBtn.setAttribute("disabled", "");
    status.textContent = "Transforming…";

    const result = await orchestrator.runTransform();
    if (!result.ok) {
      status.textContent = "";
      showError(errorEl, result.error);
      runBtn.removeAttribute("disabled");
      return;
    }

    status.textContent = `Transformation complete: ${result.data.rowCount} output rows.`;
    status.style.color = "#059669";
    setTimeout(() => navigate("output"), 800);
  });

  wrapper.appendChild(heading);
  wrapper.appendChild(info);
  wrapper.appendChild(runBtn);
  wrapper.appendChild(status);
  contentEl.appendChild(wrapper);
}
