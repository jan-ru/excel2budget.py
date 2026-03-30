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
    importWithHeaderRow: vi.fn(),
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
  const file = new File(["data"], "budget-2025.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  Object.defineProperty(input, "files", { value: [file], writable: false });
  input.dispatchEvent(new Event("change"));
  await vi.waitFor(() => {});
}

describe("Upload Screen — header row selection integration", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("shows Header_Row_Selector when importFile returns HeaderSelectionNeeded (3.1)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [2, 5],
      rawPreview: [
        ["Title", null, null],
        [null, null, null],
        ["Entity", "Account", "DC"],
        ["a", "b", "c"],
        [null, null, null],
        ["Entity", "Account", "DC"],
      ],
    });

    await render(ctx);
    await pickFile(contentEl);

    const selector = contentEl.querySelector("[data-header-selector]");
    expect(selector).not.toBeNull();

    // Verify candidate rows are rendered as options
    const options = selector!.querySelectorAll("option:not([disabled])");
    expect(options.length).toBe(2);
    expect((options[0] as HTMLOptionElement).textContent).toContain("Row 3");
    expect((options[1] as HTMLOptionElement).textContent).toContain("Row 6");
  });

  it("shows Header_Row_Selector after sheet selection when importWithSheet returns HeaderSelectionNeeded", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsSelection: true,
      sheetNames: ["Data"],
    });
    (orchestrator.importWithSheet as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [3],
      rawPreview: [
        ["Title", null, null],
        [null, null, null],
        [null, null, null],
        ["Entity", "Account", "DC"],
      ],
    });

    await render(ctx);
    await pickFile(contentEl);

    // Select sheet and confirm
    const sheetSelector = contentEl.querySelector("[data-sheet-selector]")!;
    const select = sheetSelector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = sheetSelector.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLButtonElement;

    select.value = "Data";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    await vi.waitFor(() => {
      expect(orchestrator.importWithSheet).toHaveBeenCalledWith("Data");
    });

    // Sheet selector should be removed, header selector should appear
    expect(contentEl.querySelector("[data-sheet-selector]")).toBeNull();
    const headerSelector = contentEl.querySelector("[data-header-selector]");
    expect(headerSelector).not.toBeNull();
  });

  it("navigates to preview after successful header row selection", async () => {
    const { ctx, contentEl, navigate, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [2],
      rawPreview: [
        ["Title", null, null],
        [null, null, null],
        ["Entity", "Account", "DC"],
      ],
    });
    (orchestrator.importWithHeaderRow as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 10, columns: [{ name: "Entity" }, { name: "Account" }], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    const selector = contentEl.querySelector("[data-header-selector]")!;
    const select = selector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;

    select.value = "2";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    await vi.waitFor(() => {
      expect(orchestrator.importWithHeaderRow).toHaveBeenCalledWith(2);
    });

    vi.advanceTimersByTime(700);
    expect(navigate).toHaveBeenCalledWith("preview");
  });

  it("shows error and keeps Header_Row_Selector visible on failed header selection (7.1)", async () => {
    const { ctx, contentEl, errorEl, navigate, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [2, 5],
      rawPreview: [
        ["Title", null, null],
        [null, null, null],
        ["Entity", "Account", "DC"],
        ["a", "b", "c"],
        [null, null, null],
        ["Entity", "Account", "DC"],
      ],
    });
    (orchestrator.importWithHeaderRow as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      error: "[extract_mapping] Missing columns: DC",
    });

    await render(ctx);
    await pickFile(contentEl);

    const selector = contentEl.querySelector("[data-header-selector]")!;
    const select = selector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;

    select.value = "2";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    await vi.waitFor(() => {
      expect(orchestrator.importWithHeaderRow).toHaveBeenCalledWith(2);
    });

    // Error should be shown
    expect(errorEl.textContent).toContain("Missing columns: DC");
    // Header selector should still be visible
    expect(contentEl.querySelector("[data-header-selector]")).not.toBeNull();
    // Should NOT navigate
    expect(navigate).not.toHaveBeenCalled();
  });

  it("cancel resets to initial state and clears summary (7.3, 5.5)", async () => {
    const { ctx, contentEl, errorEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [2],
      rawPreview: [
        ["Title", null, null],
        [null, null, null],
        ["Entity", "Account", "DC"],
      ],
    });

    await render(ctx);
    await pickFile(contentEl);

    // Header selector should be visible
    expect(contentEl.querySelector("[data-header-selector]")).not.toBeNull();
    // Summary should show file and sheet
    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.textContent).toContain("budget-2025.xlsx");

    // Click cancel
    const cancelBtn = contentEl.querySelector(
      '[aria-label="Cancel header row selection"]',
    ) as HTMLButtonElement;
    cancelBtn.dispatchEvent(new Event("click"));

    // Orchestrator should release pending state
    expect(orchestrator.cancelPendingImport).toHaveBeenCalledOnce();
    // Header selector should be removed
    expect(contentEl.querySelector("[data-header-selector]")).toBeNull();
    // Error area should be cleared
    expect(errorEl.innerHTML).toBe("");
    // File input should be cleared
    const input = contentEl.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input.value).toBe("");
    // Summary should be cleared
    expect(summary.style.display).toBe("none");
    expect(summary.textContent).toBe("");
  });
});

describe("Upload Screen — progressive summary", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("shows filename after file selection (5.1)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 5, columns: [{ name: "A" }], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.textContent).toContain("File");
    expect(summary.textContent).toContain("budget-2025.xlsx");
  });

  it("shows sheet name after auto-detection of Budget sheet (5.2)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 5, columns: [{ name: "A" }], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.textContent).toContain("Sheet");
    expect(summary.textContent).toContain("Budget");
  });

  it("shows header row after auto-detection (5.3)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 5, columns: [{ name: "A" }], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.textContent).toContain("Header row");
    expect(summary.textContent).toContain("Row 1");
  });

  it("shows header row with correct 1-based number after user selection (5.3)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [4],
      rawPreview: Array.from({ length: 5 }, () => ["a", "b", "c"]),
    });
    (orchestrator.importWithHeaderRow as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      data: { rowCount: 3, columns: [{ name: "Entity" }], rows: [] },
    });

    await render(ctx);
    await pickFile(contentEl);

    const selector = contentEl.querySelector("[data-header-selector]")!;
    const select = selector.querySelector("select") as HTMLSelectElement;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm header row selection"]',
    ) as HTMLButtonElement;

    select.value = "4";
    select.dispatchEvent(new Event("change"));
    confirmBtn.dispatchEvent(new Event("click"));

    await vi.waitFor(() => {
      expect(orchestrator.importWithHeaderRow).toHaveBeenCalledWith(4);
    });

    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.textContent).toContain("Header row");
    expect(summary.textContent).toContain("Row 5");
  });

  it("clears summary on cancel (5.5)", async () => {
    const { ctx, contentEl, orchestrator } = createCtx();
    (orchestrator.importFile as ReturnType<typeof vi.fn>).mockResolvedValue({
      needsHeaderSelection: true,
      candidateRows: [2],
      rawPreview: [["a"], ["b"], ["Entity", "Account", "DC"]],
    });

    await render(ctx);
    await pickFile(contentEl);

    const summary = contentEl.querySelector("[data-progress-summary]") as HTMLElement;
    expect(summary.style.display).toBe("block");

    const cancelBtn = contentEl.querySelector(
      '[aria-label="Cancel header row selection"]',
    ) as HTMLButtonElement;
    cancelBtn.dispatchEvent(new Event("click"));

    expect(summary.style.display).toBe("none");
    expect(summary.textContent).toBe("");
  });
});
