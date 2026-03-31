/**
 * Output screen: display transformed data in IronCalc spreadsheet preview.
 * Export buttons for CSV, Excel, PDF.
 * Requirements: 10.1, 11.1, 11.2, 11.3, 14.1
 */

import "@ui5/webcomponents/dist/Button.js";

import type { ScreenContext } from "../app";
import { showError } from "../components/error-banner";
import { loadData, renderToElement } from "../../engine/ironcalc-engine";
import { downloadCsv, downloadExcel } from "../../export/csv-excel-exporter";
import { downloadPdf } from "../../export/pdf-exporter";
import { cellValueToString } from "../../export/csv-excel-exporter";

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator } = ctx;
  const data = orchestrator.transformResult;

  if (!data) {
    showError(errorEl, "No transformed data available. Please run the transformation first.");
    return;
  }

  // Summary
  const summary = document.createElement("div");
  summary.style.cssText = "margin-bottom:12px;";
  summary.innerHTML =
    `<strong>Output:</strong> ${data.rowCount} rows, ${data.columns.length} columns`;

  // Export buttons
  const btnBar = document.createElement("div");
  btnBar.style.cssText = "display:flex;gap:8px;margin-bottom:16px;";

  const csvBtn = exportButton("Export CSV", async () => downloadCsv(data, "output.csv"));
  const xlsBtn = exportButton("Export Excel", async () => downloadExcel(data, "output.xlsx"));
  const pdfBtn = exportButton("Export PDF", async () => {
    const textRows = data.rows.map(r => r.values.map(cellValueToString).join(" | ")).join("\n");
    const header = data.columns.map(c => c.name).join(" | ");
    await downloadPdf({
      metadata: {
        screenTitle: "Transformation Output",
        configurationName: orchestrator.template?.packageName ?? "",
        packageName: orchestrator.template?.packageName ?? "",
        templateName: orchestrator.template?.templateName ?? "",
        generatedAt: new Date().toISOString(),
      },
      content: { contentType: "SPREADSHEET", textContent: `${header}\n${textRows}` },
    }, "output.pdf");
  });

  btnBar.appendChild(csvBtn);
  btnBar.appendChild(xlsBtn);
  btnBar.appendChild(pdfBtn);

  // Spreadsheet container
  const spreadsheet = document.createElement("div");
  spreadsheet.style.cssText = "overflow:auto;max-height:65vh;";

  contentEl.appendChild(summary);
  contentEl.appendChild(btnBar);
  contentEl.appendChild(spreadsheet);

  try {
    const handle = await loadData(data, "Output");
    renderToElement(handle, spreadsheet);
  } catch (err) {
    showError(errorEl, `Output preview failed: ${(err as Error).message}`);
  }

  // PDF options for header button
  ctx.getPdfOptions = () => {
    const header = data.columns.map(c => c.name).join(" | ");
    const textRows = data.rows.map(r => r.values.map(cellValueToString).join(" | ")).join("\n");
    return {
      metadata: {
        screenTitle: "Transformation Output",
        configurationName: orchestrator.template?.packageName ?? "",
        packageName: orchestrator.template?.packageName ?? "",
        templateName: orchestrator.template?.templateName ?? "",
        generatedAt: new Date().toISOString(),
      },
      content: { contentType: "SPREADSHEET", textContent: `${header}\n${textRows}` },
    };
  };
}

function exportButton(text: string, onClick: () => Promise<void>): HTMLElement {
  const btn = document.createElement("ui5-button");
  btn.textContent = text;
  btn.setAttribute("design", "Default");
  btn.addEventListener("click", () => onClick());
  return btn;
}
