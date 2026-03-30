// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { createSheetSelector } from "../../src/ui/components/sheet-selector";

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
    ) as HTMLButtonElement;
    expect(confirmBtn).not.toBeNull();
    expect(confirmBtn.disabled).toBe(true);
  });

  it("Confirm button becomes enabled after selecting a sheet", () => {
    const element = createSheetSelector({
      sheetNames,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const select = element.querySelector(
      '[aria-label="Sheet selection"]',
    ) as HTMLSelectElement;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLButtonElement;

    select.value = "Expenses";
    select.dispatchEvent(new Event("change"));

    expect(confirmBtn.disabled).toBe(false);
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
    ) as HTMLButtonElement;
    cancelBtn.dispatchEvent(new Event("click"));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("Confirm button calls onConfirm with the selected sheet name (3.3)", () => {
    const onConfirm = vi.fn();
    const element = createSheetSelector({
      sheetNames,
      onConfirm,
      onCancel: vi.fn(),
    });

    const select = element.querySelector(
      '[aria-label="Sheet selection"]',
    ) as HTMLSelectElement;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLButtonElement;

    select.value = "Summary";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith("Summary");
  });
});
