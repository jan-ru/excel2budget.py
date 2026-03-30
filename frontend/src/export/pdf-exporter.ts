/**
 * Client-side PDF generation for screen content.
 *
 * Uses jsPDF to produce downloadable PDFs entirely in the browser.
 * Supports spreadsheet tables, diagrams, and control tables with
 * metadata headers (screen title, configuration, package, template,
 * generation timestamp).
 *
 * Requirements: 11.3, 11.4
 */

import type { components } from "../types/api";

type ScreenContentType = components["schemas"]["ScreenContentType"];
type PDFMetadata = components["schemas"]["PDFMetadata"];

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/** Content payload passed to the PDF exporter. */
export interface PDFContent {
  contentType: ScreenContentType;
  /** Plain-text or pre-rendered string content (table rows, diagram text, etc.) */
  textContent: string;
}

export interface PDFExportOptions {
  metadata: PDFMetadata;
  content: PDFContent;
}

// ---------------------------------------------------------------------------
// PDF generation
// ---------------------------------------------------------------------------

/**
 * Generate a PDF document as a Uint8Array.
 *
 * The PDF includes a metadata header block followed by the screen content.
 */
export async function generatePdf(
  options: PDFExportOptions,
): Promise<Uint8Array> {
  const { default: jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });

  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 15;
  const usableWidth = pageWidth - margin * 2;
  let y = margin;

  // --- Metadata header ---
  doc.setFontSize(16);
  if (options.metadata.screenTitle) {
    doc.text(options.metadata.screenTitle, margin, y);
    y += 8;
  }

  doc.setFontSize(10);
  const metaLines: string[] = [];
  if (options.metadata.configurationName) {
    metaLines.push(`Configuration: ${options.metadata.configurationName}`);
  }
  if (options.metadata.packageName) {
    metaLines.push(`Package: ${options.metadata.packageName}`);
  }
  if (options.metadata.templateName) {
    metaLines.push(`Template: ${options.metadata.templateName}`);
  }
  if (options.metadata.generatedAt) {
    metaLines.push(`Generated: ${options.metadata.generatedAt}`);
  }

  for (const line of metaLines) {
    doc.text(line, margin, y);
    y += 5;
  }

  // Separator line
  if (metaLines.length > 0) {
    y += 2;
    doc.setDrawColor(200);
    doc.line(margin, y, margin + usableWidth, y);
    y += 6;
  }

  // --- Content body ---
  doc.setFontSize(10);
  const lines = doc.splitTextToSize(options.content.textContent, usableWidth);
  const lineHeight = 5;
  const pageHeight = doc.internal.pageSize.getHeight();

  for (const line of lines) {
    if (y + lineHeight > pageHeight - margin) {
      doc.addPage();
      y = margin;
    }
    doc.text(line, margin, y);
    y += lineHeight;
  }

  const arrayBuffer = doc.output("arraybuffer");
  return new Uint8Array(arrayBuffer as ArrayBuffer);
}

/**
 * Generate a PDF and trigger a browser download.
 */
export async function downloadPdf(
  options: PDFExportOptions,
  filename: string = "export.pdf",
): Promise<void> {
  const bytes = await generatePdf(options);
  const blob = new Blob([bytes.buffer as ArrayBuffer], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
