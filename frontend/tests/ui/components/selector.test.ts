/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeAll } from "vitest";
import fc from "fast-check";
import { createSheetSelector } from "../../../src/ui/components/sheet-selector";
import { createHeaderRowSelector } from "../../../src/ui/components/header-row-selector";
import { registerAllUI5Stubs } from "../helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

/** Arbitrary for non-empty sheet name lists with unique values. */
const arbSheetNames = fc
  .uniqueArray(
    fc.stringOf(fc.char().filter((c) => c.trim() === c && c !== ""), {
      minLength: 1,
      maxLength: 20,
    }),
    { minLength: 1, maxLength: 15 },
  );

/** Arbitrary for non-empty candidate row index lists with unique values. */
const arbRowIndices = fc.uniqueArray(fc.integer({ min: 0, max: 99 }), {
  minLength: 1,
  maxLength: 15,
});

// ---------------------------------------------------------------------------
// Feature: ui5-migration, Property 5: Selector components render correct UI5 structure
// ---------------------------------------------------------------------------
describe("Property 5: Selector components render correct UI5 structure", () => {
  it("sheet selector renders ui5-select with correct ui5-option count and button designs", () => {
    fc.assert(
      fc.property(arbSheetNames, (sheetNames) => {
        const el = createSheetSelector({
          sheetNames,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const select = el.querySelector("ui5-select");
        expect(select).not.toBeNull();

        // Options = placeholder + one per sheet name
        const options = select!.querySelectorAll("ui5-option");
        expect(options.length).toBe(sheetNames.length + 1);

        // Each sheet name has a matching option
        for (const name of sheetNames) {
          const match = Array.from(options).find(
            (o) => o.getAttribute("value") === name,
          );
          expect(match).toBeDefined();
        }

        // Confirm button: Emphasized
        const buttons = el.querySelectorAll("ui5-button");
        expect(buttons.length).toBe(2);
        const confirm = Array.from(buttons).find(
          (b) => b.textContent === "Confirm",
        );
        const cancel = Array.from(buttons).find(
          (b) => b.textContent === "Cancel",
        );
        expect(confirm?.getAttribute("design")).toBe("Emphasized");
        expect(cancel?.getAttribute("design")).toBe("Transparent");
      }),
      { numRuns: 100 },
    );
  });

  it("header-row selector renders ui5-select with correct ui5-option count and button designs", () => {
    fc.assert(
      fc.property(arbRowIndices, (indices) => {
        const rawPreview = indices.map((i) => [`cell-${i}-0`, `cell-${i}-1`, `cell-${i}-2`]);
        const el = createHeaderRowSelector({
          candidateRows: indices,
          rawPreview,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const select = el.querySelector("ui5-select");
        expect(select).not.toBeNull();

        // Options = placeholder + one per candidate row
        const options = select!.querySelectorAll("ui5-option");
        expect(options.length).toBe(indices.length + 1);

        // Each index has a matching option
        for (const idx of indices) {
          const match = Array.from(options).find(
            (o) => o.getAttribute("value") === String(idx),
          );
          expect(match).toBeDefined();
        }

        // Confirm button: Emphasized, Cancel: Transparent
        const buttons = el.querySelectorAll("ui5-button");
        expect(buttons.length).toBe(2);
        const confirm = Array.from(buttons).find(
          (b) => b.textContent === "Confirm",
        );
        const cancel = Array.from(buttons).find(
          (b) => b.textContent === "Cancel",
        );
        expect(confirm?.getAttribute("design")).toBe("Emphasized");
        expect(cancel?.getAttribute("design")).toBe("Transparent");
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Feature: ui5-migration, Property 6: Selector enable-on-select
// ---------------------------------------------------------------------------
describe("Property 6: Selector enable-on-select", () => {
  it("sheet selector confirm button is disabled initially", () => {
    fc.assert(
      fc.property(arbSheetNames, (sheetNames) => {
        const el = createSheetSelector({
          sheetNames,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
          (b) => b.textContent === "Confirm",
        );
        expect(confirm?.hasAttribute("disabled")).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("sheet selector confirm button enables after change event with selected option", () => {
    fc.assert(
      fc.property(arbSheetNames, (sheetNames) => {
        const el = createSheetSelector({
          sheetNames,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const select = el.querySelector("ui5-select")!;
        const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
          (b) => b.textContent === "Confirm",
        )!;

        // Simulate UI5 change event with a selected option
        const fakeOption = { getAttribute: () => sheetNames[0], value: sheetNames[0] };
        const changeEvent = new CustomEvent("change", {
          detail: { selectedOption: fakeOption },
          bubbles: true,
        });
        select.dispatchEvent(changeEvent);

        expect(confirm.hasAttribute("disabled")).toBe(false);
      }),
      { numRuns: 100 },
    );
  });

  it("header-row selector confirm button is disabled initially", () => {
    fc.assert(
      fc.property(arbRowIndices, (indices) => {
        const rawPreview = indices.map(() => ["a", "b", "c"]);
        const el = createHeaderRowSelector({
          candidateRows: indices,
          rawPreview,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
          (b) => b.textContent === "Confirm",
        );
        expect(confirm?.hasAttribute("disabled")).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("header-row selector confirm button enables after change event", () => {
    fc.assert(
      fc.property(arbRowIndices, (indices) => {
        const rawPreview = indices.map(() => ["a", "b", "c"]);
        const el = createHeaderRowSelector({
          candidateRows: indices,
          rawPreview,
          onConfirm: () => {},
          onCancel: () => {},
        });

        const select = el.querySelector("ui5-select")!;
        const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
          (b) => b.textContent === "Confirm",
        )!;

        const fakeOption = { getAttribute: () => String(indices[0]), value: String(indices[0]) };
        const changeEvent = new CustomEvent("change", {
          detail: { selectedOption: fakeOption },
          bubbles: true,
        });
        select.dispatchEvent(changeEvent);

        expect(confirm.hasAttribute("disabled")).toBe(false);
      }),
      { numRuns: 100 },
    );
  });
});

// ---------------------------------------------------------------------------
// Feature: ui5-migration, Property 7: Selector confirm callback delivers selected value
// ---------------------------------------------------------------------------
describe("Property 7: Selector confirm callback delivers selected value", () => {
  it("sheet selector confirm delivers the selected sheet name", () => {
    fc.assert(
      fc.property(
        arbSheetNames,
        fc.nat(),
        (sheetNames, rawIdx) => {
          const idx = rawIdx % sheetNames.length;
          const selectedName = sheetNames[idx];
          let received: string | undefined;

          const el = createSheetSelector({
            sheetNames,
            onConfirm: (v) => { received = v; },
            onCancel: () => {},
          });

          const select = el.querySelector("ui5-select")!;

          // Mark the target option as selected (simulate UI5 behavior)
          const targetOpt = Array.from(select.querySelectorAll("ui5-option")).find(
            (o) => o.getAttribute("value") === selectedName,
          );
          if (targetOpt) {
            // Remove selected from placeholder
            const placeholder = select.querySelector("ui5-option[disabled]");
            placeholder?.removeAttribute("selected");
            targetOpt.setAttribute("selected", "");
          }

          // Fire change to enable confirm
          const fakeOption = { getAttribute: () => selectedName, value: selectedName };
          select.dispatchEvent(
            new CustomEvent("change", { detail: { selectedOption: fakeOption }, bubbles: true }),
          );

          // Click confirm
          const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
            (b) => b.textContent === "Confirm",
          )!;
          confirm.click();

          expect(received).toBe(selectedName);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("header-row selector confirm delivers the selected row index", () => {
    fc.assert(
      fc.property(
        arbRowIndices,
        fc.nat(),
        (indices, rawIdx) => {
          const idx = rawIdx % indices.length;
          const selectedIndex = indices[idx];
          let received: number | undefined;

          const rawPreview = indices.map(() => ["a", "b", "c"]);
          const el = createHeaderRowSelector({
            candidateRows: indices,
            rawPreview,
            onConfirm: (v) => { received = v; },
            onCancel: () => {},
          });

          const select = el.querySelector("ui5-select")!;

          // Mark the target option as selected
          const targetOpt = Array.from(select.querySelectorAll("ui5-option")).find(
            (o) => o.getAttribute("value") === String(selectedIndex),
          );
          if (targetOpt) {
            const placeholder = select.querySelector("ui5-option[disabled]");
            placeholder?.removeAttribute("selected");
            targetOpt.setAttribute("selected", "");
          }

          // Fire change to enable confirm
          const fakeOption = { getAttribute: () => String(selectedIndex), value: String(selectedIndex) };
          select.dispatchEvent(
            new CustomEvent("change", { detail: { selectedOption: fakeOption }, bubbles: true }),
          );

          // Click confirm
          const confirm = Array.from(el.querySelectorAll("ui5-button")).find(
            (b) => b.textContent === "Confirm",
          )!;
          confirm.click();

          expect(received).toBe(selectedIndex);
        },
      ),
      { numRuns: 100 },
    );
  });
});
