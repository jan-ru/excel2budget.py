// @vitest-environment jsdom
import { describe, it, expect, vi, beforeAll } from "vitest";
import { createSheetSelector } from "../../src/ui/components/sheet-selector";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

/** Simulate a UI5 select change event. */
function fireUI5Change(select: Element, value: string) {
  const fakeOption = { getAttribute: () => value, value };
  select.dispatchEvent(
    new CustomEvent("change", { detail: { selectedOption: fakeOption }, bubbles: true }),
  );
}

/** Mark an option as selected and remove selected from placeholder. */
function selectOption(select: Element, value: string) {
  const placeholder = select.querySelector("ui5-option[disabled]");
  placeholder?.removeAttribute("selected");
  const opt = Array.from(select.querySelectorAll("ui5-option")).find(
    (o) => o.getAttribute("value") === value,
  );
  opt?.setAttribute("selected", "");
  fireUI5Change(select, value);
}

describe("Sheet Selector behavior", () => {
  const sheetNames = ["Sales", "Expenses", "Summary"];

  it("Confirm button is disabled on initial render (3.5)", () => {
    const element = createSheetSelector({
      sheetNames,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const confirmBtn = element.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLElement;
    expect(confirmBtn).not.toBeNull();
    expect(confirmBtn.hasAttribute("disabled")).toBe(true);
  });

  it("Confirm button becomes enabled after selecting a sheet", () => {
    const element = createSheetSelector({
      sheetNames,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const select = element.querySelector("ui5-select")!;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLElement;

    selectOption(select, "Expenses");

    expect(confirmBtn.hasAttribute("disabled")).toBe(false);
  });

  it("Cancel button calls onCancel (3.4)", () => {
    const onCancel = vi.fn();
    const element = createSheetSelector({
      sheetNames,
      onConfirm: vi.fn(),
      onCancel,
    });

    const cancelBtn = element.querySelector(
      '[aria-label="Cancel sheet selection"]',
    ) as HTMLElement;
    cancelBtn.click();

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("Confirm button calls onConfirm with the selected sheet name (3.3)", () => {
    const onConfirm = vi.fn();
    const element = createSheetSelector({
      sheetNames,
      onConfirm,
      onCancel: vi.fn(),
    });

    const select = element.querySelector("ui5-select")!;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLElement;

    selectOption(select, "Summary");
    confirmBtn.click();

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith("Summary");
  });
});
