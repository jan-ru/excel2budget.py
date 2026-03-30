// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "../../src/ui/screens/upload";
import type { ScreenContext, ScreenName } from "../../src/ui/app";
import type { PipelineOrchestrator } from "../../src/pipeline/orchestrator";

/** Helper to build a minimal ScreenContext with a mock orchestrator. */
function createCtx(overrides: Partial<PipelineOrchestrator> = {}) {
  const contentEl = document.createElement("div");
  const errorEl = document.createElement("div");
  const navigate = vi.fn<(screen: ScreenName) => void>();

  const orchestrator = {
    importFile: vi.fn(),
    importWithSheet: vi.fn(),
    cancelPendingImport: vi.fn(),
    ...overrides,
  } as unknown as PipelineOrchestrator;

  const ctx: ScreenContext = {
    contentEl,
    errorEl,
    orchestrator,
    navigate,
    getPdfOptions: () => null,
  };

  return { ctx, contentEl, errorEl, navigate, orchestrator };
}

/** Simulate selecting a file on the input element. */
async function pickFile(contentEl: HTMLElement): Promise<void> {
  const input = contentEl.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  // Provide a fake file via the files property
  const file = new File(["data"], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  Object.defineProperty(input, "files", { value: [file], writable: false });
  input.dispatchEvent(new Event("change"));
  // Let async handler settle
  await vi.waitFor(() => {});
}

describe("Upload Screen — sheet selection integration", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("shows sheet selector when importFile returns SheetSelectionNeeded (3.1)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsSelection: true,
      sheetNames: ["Sales", "Expenses"],
    });

    await render(ctx);
    await pickFile(contentEl);

    const selector = contentEl.querySelector("[data-sheet-selector]");
    expect(selector).not.toBeNull();

    // Verify sheet names are rendered as options
    const options = selector!.querySelectorAll("option:not([disabled])");
    expect(options.length).toBe(2);
    expect((options[0] as HTMLOptionElement).value).toBe("Sales");
    expect((options[1] as HTMLOptionElement).value).toBe("Expenses");
  });

  it("navigates to preview on successful sheet selection", async () => {
    const { ctx, contentEl, errorEl, navigate, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsSelection: true,
      sheetNames: ["Sales", "Expenses"],
    });
    (orchestrator.importWithSheet as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 5, columns: ["A", "B"], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    // Select a sheet and confirm
    const selector = contentEl.querySelector("[data-sheet-selector]")!;
    const select = selector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLButtonElement;

    select.value = "Sales";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    // Let async handler settle
    await vi.waitFor(() => {
      expect(orchestrator.importWithSheet).toHaveBeenCalledWith("Sales");
    });

    // Navigate after timeout
    vi.advanceTimersByTime(700);
    expect(navigate).toHaveBeenCalledWith("preview");
  });

  it("shows error and keeps selector visible on failed sheet selection (6.2)", async () => {
    const { ctx, contentEl, errorEl, navigate, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsSelection: true,
      sheetNames: ["Sales", "Expenses"],
    });
    (orchestrator.importWithSheet as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      error: "Sheet 'Sales' is empty",
    });

    await render(ctx);
    await pickFile(contentEl);

    // Select a sheet and confirm
    const selector = contentEl.querySelector("[data-sheet-selector]")!;
    const select = selector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLButtonElement;

    select.value = "Sales";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    await vi.waitFor(() => {
      expect(orchestrator.importWithSheet).toHaveBeenCalledWith("Sales");
    });

    // Error should be shown
    expect(errorEl.textContent).toContain("Sheet 'Sales' is empty");
    // Selector should still be visible
    expect(contentEl.querySelector("[data-sheet-selector]")).not.toBeNull();
    // Should NOT navigate
    expect(navigate).not.toHaveBeenCalled();
  });

  it("cancel resets to initial upload state (5.1, 5.2)", async () => {
    const { ctx, contentEl, errorEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsSelection: true,
      sheetNames: ["Sales"],
    });

    await render(ctx);
    await pickFile(contentEl);

    // Selector should be visible
    expect(contentEl.querySelector("[data-sheet-selector]")).not.toBeNull();

    // Click cancel
    const cancelBtn = contentEl.querySelector(
      '[aria-label="Cancel sheet selection"]',
    ) as HTMLButtonElement;
    cancelBtn.dispatchEvent(new Event("click"));

    // Orchestrator should release workbook
    expect(orchestrator.cancelPendingImport).toHaveBeenCalledOnce();
    // Selector should be removed
    expect(contentEl.querySelector("[data-sheet-selector]")).toBeNull();
    // Error area should be cleared
    expect(errorEl.innerHTML).toBe("");
    // File input should be cleared
    const input = contentEl.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    expect(input.value).toBe("");
  });
});
