/**
 * Header component: current date display (YYYY-MM-DD) + "Download as PDF" action.
 * Requirements: 2.1, 2.2, 2.3, 11.1
 */

import "@ui5/webcomponents/dist/Button.js";
import { downloadPdf } from "../../export/pdf-exporter";
import type { PDFExportOptions } from "../../export/pdf-exporter";

export interface HeaderOptions {
  /** Called to build PDF export options from the current screen state. */
  getPdfOptions?: () => PDFExportOptions | null;
}

/** Format today's date as YYYY-MM-DD. */
function todayString(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Create and return the header element. */
export function createHeader(options: HeaderOptions = {}): HTMLElement {
  const header = document.createElement("header");
  header.style.cssText =
    "display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #e5e7eb;background:#fff;";

  const left = document.createElement("div");
  left.style.cssText = "display:flex;align-items:center;gap:16px;";

  const title = document.createElement("span");
  title.style.cssText = "font-weight:600;font-size:16px;";
  title.textContent = "Data Conversion Tool";

  const dateEl = document.createElement("span");
  dateEl.style.cssText = "color:#6b7280;font-size:13px;";
  dateEl.textContent = todayString();

  left.appendChild(title);
  left.appendChild(dateEl);

  const pdfBtn = document.createElement("ui5-button");
  pdfBtn.textContent = "Download as PDF";
  pdfBtn.setAttribute("design", "Default");
  pdfBtn.addEventListener("click", async () => {
    const opts = options.getPdfOptions?.();
    if (opts) {
      await downloadPdf(opts, "export.pdf");
    }
  });

  header.appendChild(left);
  header.appendChild(pdfBtn);
  return header;
}
