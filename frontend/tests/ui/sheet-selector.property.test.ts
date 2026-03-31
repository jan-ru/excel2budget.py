// @vitest-environment jsdom
import { describe, it, expect, beforeAll } from "vitest";
import fc from "fast-check";
import { createSheetSelector } from "../../src/ui/components/sheet-selector";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

// Feature: dynamic-sheet-selection, Property 3: Sheet selector renders all provided names

describe("Property 3: Sheet selector renders all provided names", () => {
  it("renders exactly one <ui5-option> per sheet name in the same order (excluding placeholder)", () => {
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

          const select = element.querySelector("ui5-select")!;
          expect(select).not.toBeNull();

          const allOptions = Array.from(select.querySelectorAll("ui5-option"));

          // First option is the disabled placeholder with empty value
          const placeholder = allOptions[0];
          expect(placeholder.getAttribute("value")).toBe("");
          expect(placeholder.hasAttribute("disabled")).toBe(true);

          // Remaining options (excluding placeholder) should match input array
          const sheetOptions = allOptions.slice(1);
          expect(sheetOptions).toHaveLength(sheetNames.length);

          for (let i = 0; i < sheetNames.length; i++) {
            expect(sheetOptions[i].getAttribute("value")).toBe(sheetNames[i]);
            expect(sheetOptions[i].textContent).toBe(sheetNames[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
