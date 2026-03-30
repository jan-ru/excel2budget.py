// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { createHeaderRowSelector } from "../../src/ui/components/header-row-selector";

const rawPreview: unknown[][] = [
  ["Title", "Report", "2024"],
  ["Entity", "Account", "DC", "Jan", "Feb"],
  ["Dept A", "Revenue", "D", 100, 200],
  ["Dept B", "Expense", "C", 50, 75],
];

describe("Header Row Selector behavior", () => {
  it("Confirm button is disabled on initial render (3.6)", () => {
    const element = createHeaderRowSelector({
      candidateRows: [1],
      rawPreview,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const confirmBtn = element.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;
    expect(confirmBtn).not.toBeNull();
    expect(confirmBtn.disabled).toBe(true);
  });

  it("Confirm button becomes enabled after selecting a row", () => {
    const element = createHeaderRowSelector({
      candidateRows: [1],
      rawPreview,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const select = element.querySelector(
      '[aria-label="Header row selection"]',
    ) as HTMLSelectElement;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;

    select.value = "1";
    select.dispatchEvent(new Event("change"));

    expect(confirmBtn.disabled).toBe(false);
  });

  it("Cancel calls onCancel (3.5)", () => {
    const onCancel = vi.fn();
    const element = createHeaderRowSelector({
      candidateRows: [1],
      rawPreview,
      onConfirm: vi.fn(),
      onCancel,
    });

    const cancelBtn = element.querySelector(
      '[aria-label="Cancel header row selection"]',
    ) as HTMLButtonElement;
    cancelBtn.dispatchEvent(new Event("click"));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("Confirm calls onConfirm with correct zero-based index (3.4)", () => {
    const onConfirm = vi.fn();
    const element = createHeaderRowSelector({
      candidateRows: [1, 3],
      rawPreview,
      onConfirm,
      onCancel: vi.fn(),
    });

    const select = element.querySelector(
      '[aria-label="Header row selection"]',
    ) as HTMLSelectElement;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;

    select.value = "3";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith(3);
  });

  it("Empty candidates shows all rows up to 20 (3.3)", () => {
    const element = createHeaderRowSelector({
      candidateRows: [],
      rawPreview,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const select = element.querySelector(
      '[aria-label="Header row selection"]',
    ) as HTMLSelectElement;
    const allOptions = Array.from(select.querySelectorAll("option"));
    // placeholder + 4 rows (rawPreview has 4 rows, which is < 20)
    expect(allOptions).toHaveLength(1 + rawPreview.length);

    // Verify 1-based labels
    for (let i = 0; i < rawPreview.length; i++) {
      expect(allOptions[i + 1].textContent).toContain(`Row ${i + 1}:`);
      expect(allOptions[i + 1].value).toBe(String(i));
    }
  });
});
