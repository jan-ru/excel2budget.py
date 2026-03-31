// @vitest-environment jsdom
import { describe, it, expect, vi, beforeAll } from "vitest";
import { createHeaderRowSelector } from "../../src/ui/components/header-row-selector";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

const rawPreview: unknown[][] = [
  ["Title", "Report", "2024"],
  ["Entity", "Account", "DC", "Jan", "Feb"],
  ["Dept A", "Revenue", "D", 100, 200],
  ["Dept B", "Expense", "C", 50, 75],
];

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
    ) as HTMLElement;
    expect(confirmBtn).not.toBeNull();
    expect(confirmBtn.hasAttribute("disabled")).toBe(true);
  });

  it("Confirm button becomes enabled after selecting a row", () => {
    const element = createHeaderRowSelector({
      candidateRows: [1],
      rawPreview,
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    });

    const select = element.querySelector("ui5-select")!;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLElement;

    selectOption(select, "1");

    expect(confirmBtn.hasAttribute("disabled")).toBe(false);
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
    ) as HTMLElement;
    cancelBtn.click();

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

    const select = element.querySelector("ui5-select")!;
    const confirmBtn = element.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLElement;

    selectOption(select, "3");
    confirmBtn.click();

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

    const select = element.querySelector("ui5-select")!;
    const allOptions = Array.from(select.querySelectorAll("ui5-option"));
    // placeholder + 4 rows (rawPreview has 4 rows, which is < 20)
    expect(allOptions).toHaveLength(1 + rawPreview.length);

    // Verify 1-based labels
    for (let i = 0; i < rawPreview.length; i++) {
      expect(allOptions[i + 1].textContent).toContain(`Row ${i + 1}:`);
      expect(allOptions[i + 1].getAttribute("value")).toBe(String(i));
    }
  });
});
