/**
 * Upload screen: file input accepting .xlsx, triggers Pipeline_Orchestrator.importFile.
 * Shows error banner on failure. Handles sheet selection when no "Budget" sheet exists.
 * Handles header row selection when required columns are not auto-detected.
 * Displays progressive summary of resolved import variables.
 * Requirements: 3.1, 4.1, 5.1, 5.2, 5.3, 5.4, 5.5, 6.2, 7.1, 7.3, 14.1
 */

import "@ui5/webcomponents/dist/FileUploader.js";

import type { ScreenContext } from "../app";
import { showError, clearError } from "../components/error-banner";
import { isSheetSelectionNeeded, isHeaderSelectionNeeded } from "../../pipeline/orchestrator";
import { createSheetSelector } from "../components/sheet-selector";
import { createHeaderRowSelector } from "../components/header-row-selector";

/** Create or update the progress summary display. */
function updateProgressSummary(
  container: HTMLElement,
  items: { label: string; value: string }[],
): void {
  container.innerHTML = "";
  if (items.length === 0) return;
  for (const { label, value } of items) {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;justify-content:space-between;padding:4px 0;font-size:13px;";
    const lbl = document.createElement("span");
    lbl.style.cssText = "color:#6b7280;";
    lbl.textContent = label;
    const val = document.createElement("span");
    val.style.cssText = "color:#111827;font-weight:500;";
    val.textContent = value;
    row.appendChild(lbl);
    row.appendChild(val);
    container.appendChild(row);
  }
}

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

  const input = document.createElement("ui5-file-uploader");
  input.setAttribute("accept", ".xlsx");
  input.setAttribute("aria-label", "Upload Excel file");

  const status = document.createElement("p");
  status.style.cssText = "font-size:14px;color:#374151;";

  // Progress summary container (Req 5.1–5.5)
  const summaryEl = document.createElement("div");
  summaryEl.setAttribute("data-progress-summary", "true");
  summaryEl.style.cssText =
    "text-align:left;margin:12px 0;padding:8px 12px;border:1px solid #e5e7eb;border-radius:6px;display:none;";

  // Track resolved import variables for progressive summary
  let summaryItems: { label: string; value: string }[] = [];

  function addSummaryItem(label: string, value: string): void {
    summaryItems.push({ label, value });
    summaryEl.style.display = "block";
    updateProgressSummary(summaryEl, summaryItems);
  }

  function clearSummary(): void {
    summaryItems = [];
    summaryEl.style.display = "none";
    updateProgressSummary(summaryEl, []);
  }

  /** Reset UI to initial upload state. */
  function resetToInitial(): void {
    clearError(errorEl);
    status.textContent = "";
    (input as unknown as HTMLInputElement).value = "";
    clearSummary();
    // Remove sheet selector if present
    const sheetSel = wrapper.querySelector("[data-sheet-selector]");
    if (sheetSel) sheetSel.remove();
    // Remove header row selector if present
    const headerSel = wrapper.querySelector("[data-header-selector]");
    if (headerSel) headerSel.remove();
  }

  /** Handle a successful import result — show summary and navigate. */
  function handleSuccess(data: { rowCount: number; columns: { name: string }[] }): void {
    status.textContent = `Imported ${data.rowCount} rows, ${data.columns.length} columns.`;
    setTimeout(() => navigate("preview"), 600);
  }

  // (handleHeaderResult removed — inline logic used instead for proper type narrowing)

  /** Show the header row selector dropdown inside the wrapper. */
  function showHeaderSelector(candidateRows: number[], rawPreview: unknown[][]): void {
    // Remove any previous header selector
    const existing = wrapper.querySelector("[data-header-selector]");
    if (existing) existing.remove();

    const selectorEl = createHeaderRowSelector({
      candidateRows,
      rawPreview,
      onConfirm: async (headerRowIndex: number) => {
        clearError(errorEl);
        status.textContent = "Importing…";
        const headerResult = await orchestrator.importWithHeaderRow(headerRowIndex);
        if (!headerResult.ok) {
          status.textContent = "";
          showError(errorEl, headerResult.error);
          // Keep header selector visible so user can pick another row or cancel (Req 7.1)
          return;
        }
        addSummaryItem("Header row", `Row ${headerRowIndex + 1}`);
        handleSuccess(headerResult.data);
      },
      onCancel: () => {
        orchestrator.cancelPendingImport();
        resetToInitial();
      },
    });
    selectorEl.setAttribute("data-header-selector", "true");
    wrapper.appendChild(selectorEl);
  }

  /** Show the sheet selector dropdown inside the wrapper. */
  function showSheetSelector(sheetNames: string[]): void {
    // Remove any previous selector
    const existing = wrapper.querySelector("[data-sheet-selector]");
    if (existing) existing.remove();

    const selectorEl = createSheetSelector({
      sheetNames,
      onConfirm: async (name: string) => {
        clearError(errorEl);
        status.textContent = "Importing…";
        const sheetResult = await orchestrator.importWithSheet(name);

        if (isSheetSelectionNeeded(sheetResult)) {
          // Should not happen after importWithSheet, but handle gracefully
          return;
        }

        // importWithSheet may now return HeaderSelectionNeeded
        if (isHeaderSelectionNeeded(sheetResult)) {
          addSummaryItem("Sheet", name);
          status.textContent = "Please select the header row.";
          // Remove sheet selector before showing header selector
          const sel = wrapper.querySelector("[data-sheet-selector]");
          if (sel) sel.remove();
          showHeaderSelector(sheetResult.candidateRows, sheetResult.rawPreview);
          return;
        }

        if (!sheetResult.ok) {
          status.textContent = "";
          showError(errorEl, sheetResult.error);
          // Keep selector visible so user can pick another sheet or cancel
          return;
        }

        addSummaryItem("Sheet", name);
        addSummaryItem("Header row", "Row 1");
        handleSuccess(sheetResult.data);
      },
      onCancel: () => {
        orchestrator.cancelPendingImport();
        resetToInitial();
      },
    });
    selectorEl.setAttribute("data-sheet-selector", "true");
    wrapper.appendChild(selectorEl);
  }

  input.addEventListener("change", async (e: Event) => {
    const file = ((e as CustomEvent).detail?.files as FileList)?.[0];
    if (!file) return;

    clearError(errorEl);
    clearSummary();
    status.textContent = "Importing…";

    // Add filename to summary (Req 5.1)
    addSummaryItem("File", file.name);

    const result = await orchestrator.importFile(file);

    if (isSheetSelectionNeeded(result)) {
      status.textContent = "Please select a sheet to import.";
      showSheetSelector(result.sheetNames);
      return;
    }

    if (isHeaderSelectionNeeded(result)) {
      addSummaryItem("Sheet", "Budget");
      status.textContent = "Please select the header row.";
      showHeaderSelector(result.candidateRows, result.rawPreview);
      return;
    }

    if (!result.ok) {
      status.textContent = "";
      showError(errorEl, result.error);
      return;
    }

    // Auto-detected: Budget sheet, row 0 header
    addSummaryItem("Sheet", "Budget");
    addSummaryItem("Header row", "Row 1");
    handleSuccess(result.data);
  });

  wrapper.appendChild(heading);
  wrapper.appendChild(desc);
  wrapper.appendChild(input);
  wrapper.appendChild(summaryEl);
  wrapper.appendChild(status);
  contentEl.appendChild(wrapper);
}
