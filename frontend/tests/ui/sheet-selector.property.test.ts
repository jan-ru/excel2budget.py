// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { createSheetSelector } from "../../src/ui/components/sheet-selector";

// Feature: dynamic-sheet-selection, Property 3: Sheet selector renders all provided names

describe("Property 3: Sheet selector renders all provided names", () => {
  // Feature: dynamic-sheet-selection, Property 3: Sheet selector renders all provided names

  it("renders exactly one <option> per sheet name in the same order (excluding placeholder)", () => {
    // **Validates: Requirements 3.2**
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1 }), { minLength: 1 }),
        (sheetNames) => {
          const element = createSheetSelector({
            sheetNames,
            onConfirm: () => {},
            onCancel: () => {},
          });

          const select = element.querySelector("select")!;
          expect(select).not.toBeNull();

          const allOptions = Array.from(select.querySelectorAll("option"));

          // First option is the disabled placeholder with empty value
          const placeholder = allOptions[0];
          expect(placeholder.value).toBe("");
          expect(placeholder.disabled).toBe(true);

          // Remaining options (excluding placeholder) should match input array
          const sheetOptions = allOptions.slice(1);
          expect(sheetOptions).toHaveLength(sheetNames.length);

          for (let i = 0; i < sheetNames.length; i++) {
            expect(sheetOptions[i].value).toBe(sheetNames[i]);
            expect(sheetOptions[i].textContent).toBe(sheetNames[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
