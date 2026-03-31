// @vitest-environment jsdom
// Feature: header-row-selection, Property 3: Header row selector renders correct options with previews
import { describe, it, expect, beforeAll } from "vitest";
import fc from "fast-check";
import { createHeaderRowSelector } from "../../src/ui/components/header-row-selector";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

describe("Property 3: Header row selector renders correct options with previews", () => {
  it("renders exactly one <ui5-option> per candidate row with 1-based numbering and first 3 cell values", () => {
    // **Validates: Requirements 3.2, 3.3**
    fc.assert(
      fc.property(
        fc.array(fc.integer({ min: 0, max: 19 }), { minLength: 1, maxLength: 10 })
          .map((arr) => [...new Set(arr)].sort((a, b) => a - b)),
        fc.array(
          fc.array(fc.oneof(fc.string(), fc.constant(null)), { minLength: 1, maxLength: 5 }),
          { minLength: 20, maxLength: 20 },
        ),
        (candidateRows, rawPreview) => {
          const element = createHeaderRowSelector({
            candidateRows,
            rawPreview,
            onConfirm: () => {},
            onCancel: () => {},
          });

          const select = element.querySelector("ui5-select")!;
          expect(select).not.toBeNull();

          const allOptions = Array.from(select.querySelectorAll("ui5-option"));
          // First option is the disabled placeholder
          const placeholder = allOptions[0];
          expect(placeholder.getAttribute("value")).toBe("");
          expect(placeholder.hasAttribute("disabled")).toBe(true);

          const rowOptions = allOptions.slice(1);
          expect(rowOptions).toHaveLength(candidateRows.length);

          for (let i = 0; i < candidateRows.length; i++) {
            const idx = candidateRows[i];
            expect(rowOptions[i].getAttribute("value")).toBe(String(idx));

            // Verify 1-based row number in label
            expect(rowOptions[i].textContent).toContain(`Row ${idx + 1}:`);

            // Verify first 3 cell values appear in label
            const row = rawPreview[idx];
            const expectedCells = row
              .slice(0, 3)
              .map((c) => (c == null ? "" : String(c).trim()));
            expect(rowOptions[i].textContent).toContain(expectedCells.join(", "));
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("renders all rows 0–min(19, length-1) when candidateRows is empty", () => {
    // **Validates: Requirements 3.3**
    fc.assert(
      fc.property(
        fc.array(
          fc.array(fc.oneof(fc.string(), fc.constant(null)), { minLength: 1, maxLength: 5 }),
          { minLength: 1, maxLength: 25 },
        ),
        (rawPreview) => {
          const element = createHeaderRowSelector({
            candidateRows: [],
            rawPreview,
            onConfirm: () => {},
            onCancel: () => {},
          });

          const select = element.querySelector("ui5-select")!;
          const rowOptions = Array.from(select.querySelectorAll("ui5-option")).slice(1);
          const expectedCount = Math.min(20, rawPreview.length);
          expect(rowOptions).toHaveLength(expectedCount);

          for (let i = 0; i < expectedCount; i++) {
            expect(rowOptions[i].getAttribute("value")).toBe(String(i));
            expect(rowOptions[i].textContent).toContain(`Row ${i + 1}:`);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
