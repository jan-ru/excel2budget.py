/**
 * Property test: Import with selected sheet extracts correct data (Property 4)
 *
 * For any workbook and for any sheet name that exists in that workbook and is
 * non-empty, calling `importWithSheet(sheetName)` SHALL return a successful
 * `Result<TabularData>` whose `metadata.sourceName` equals the provided
 * `sheetName`.
 *
 * Feature: dynamic-sheet-selection, Property 4: Import with selected sheet extracts correct data
 * Validates: Requirements 4.1, 4.2
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as XLSX from "xlsx";
import {
  PipelineOrchestrator,
  isSheetSelectionNeeded,
} from "../../src/pipeline/orchestrator";

// --- Helpers ---

/** Characters safe for Excel sheet names (no :\/?*[]') */
const SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-";

/** Arbitrary for a valid Excel sheet name that is NOT "Budget". */
const nonBudgetSheetName = fc
  .stringOf(fc.constantFrom(...SAFE_CHARS), { minLength: 1, maxLength: 20 })
  .map((s) => s.trim())
  .filter((s) => s.length > 0 && s !== "Budget");

/** Required column headers for a valid budget sheet. */
const REQUIRED_HEADERS = ["Entity", "Account", "DC", "jan-26"];

/**
 * Build a workbook with multiple non-empty sheets, each containing valid
 * headers and at least one data row. No sheet is named "Budget".
 */
function buildWorkbookWithSheets(sheetNames: string[]): XLSX.WorkBook {
  const wb = XLSX.utils.book_new();

  for (const name of sheetNames) {
    const sheetData = [
      REQUIRED_HEADERS,
      ["E1", "A1", "D", 100],
    ];
    const ws = XLSX.utils.aoa_to_sheet(sheetData);
    XLSX.utils.book_append_sheet(wb, ws, name);
  }

  return wb;
}

/** Convert a workbook to a File object (round-trip through XLSX.write). */
function workbookToFile(wb: XLSX.WorkBook): File {
  const bytes = XLSX.write(wb, { type: "array", bookType: "xlsx" }) as Uint8Array;
  return new File([bytes as BlobPart], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

// --- Property 4: Import with selected sheet extracts correct data ---

describe("Property 4: Import with selected sheet extracts correct data", () => {
  // Feature: dynamic-sheet-selection, Property 4: Import with selected sheet extracts correct data
  // **Validates: Requirements 4.1, 4.2**

  it("importWithSheet returns successful Result<TabularData> with sourceName equal to chosen sheet", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc
          .uniqueArray(nonBudgetSheetName, { minLength: 1, maxLength: 5 })
          .chain((names) =>
            fc.record({
              sheetNames: fc.constant(names),
              selectedIndex: fc.nat({ max: names.length - 1 }),
            }),
          ),
        async ({ sheetNames, selectedIndex }) => {
          const selectedSheet = sheetNames[selectedIndex];
          const wb = buildWorkbookWithSheets(sheetNames);
          const file = workbookToFile(wb);

          const orchestrator = new PipelineOrchestrator();

          // First call importFile — should return SheetSelectionNeeded (no "Budget" sheet)
          const importResult = await orchestrator.importFile(file);
          expect(isSheetSelectionNeeded(importResult)).toBe(true);

          // Now call importWithSheet with the randomly selected sheet name
          const result = await orchestrator.importWithSheet(selectedSheet);

          // Should be a successful result
          expect(result).toHaveProperty("ok", true);

          if ("ok" in result && result.ok) {
            // metadata.sourceName must equal the selected sheet name
            expect(result.data.metadata.sourceName).toBe(selectedSheet);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
