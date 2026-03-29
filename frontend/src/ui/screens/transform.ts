/**
 * Transform screen: trigger transformation via Pipeline_Orchestrator.runTransform.
 * Display success/error result.
 * Requirements: 8.3, 14.1
 */

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

  const runBtn = document.createElement("button");
  runBtn.textContent = "Run Transformation";
  runBtn.disabled = !orchestrator.sourceData || !orchestrator.template || !orchestrator.userParams;
  runBtn.style.cssText =
    "padding:10px 24px;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;";
  if (runBtn.disabled) {
    runBtn.style.opacity = "0.5";
    runBtn.style.cursor = "not-allowed";
  }

  const status = document.createElement("p");
  status.style.cssText = "margin-top:16px;font-size:14px;";

  runBtn.addEventListener("click", async () => {
    clearError(errorEl);
    runBtn.disabled = true;
    status.textContent = "Transforming…";

    const result = await orchestrator.runTransform();
    if (!result.ok) {
      status.textContent = "";
      showError(errorEl, result.error);
      runBtn.disabled = false;
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
