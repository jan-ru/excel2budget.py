/**
 * Preview screen: display imported data summary and IronCalc spreadsheet preview.
 * Requirements: 10.1, 14.1
 */

import type { ScreenContext } from "../app";
import { showError } from "../components/error-banner";
import { loadData, renderToElement } from "../../engine/ironcalc-engine";

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator, navigate } = ctx;
  const data = orchestrator.sourceData;

  if (!data) {
    showError(errorEl, "No data imported yet. Please upload a file first.");
    return;
  }

  // Summary
  const summary = document.createElement("div");
  summary.style.cssText = "margin-bottom:16px;";
  summary.innerHTML =
    `<strong>Rows:</strong> ${data.rowCount} &nbsp; <strong>Columns:</strong> ${data.columns.length}`;

  // Spreadsheet container
  const spreadsheet = document.createElement("div");
  spreadsheet.style.cssText = "overflow:auto;max-height:70vh;";

  contentEl.appendChild(summary);
  contentEl.appendChild(spreadsheet);

  try {
    const handle = await loadData(data, "Preview");
    renderToElement(handle, spreadsheet);
  } catch (err) {
    showError(errorEl, `Preview failed: ${(err as Error).message}`);
  }

  // PDF options for this screen
  ctx.getPdfOptions = () => ({
    metadata: {
      screenTitle: "Data Preview",
      configurationName: "",
      packageName: "",
      templateName: "",
      generatedAt: new Date().toISOString(),
    },
    content: {
      contentType: "SPREADSHEET",
      textContent: `Rows: ${data.rowCount}, Columns: ${data.columns.length}`,
    },
  });
}
