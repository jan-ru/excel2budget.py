// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render } from "../../src/ui/screens/upload";
import type { ScreenContext, ScreenName } from "../../src/ui/app";
import type { PipelineOrchestrator } from "../../src/pipeline/orchestrator";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

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

/** Simulate selecting a file on the ui5-file-uploader element. */
async function pickFile(contentEl: HTMLElement): Promise<void> {
  const input = contentEl.querySelector(
    "ui5-file-uploader",
  ) as HTMLElement;
  const file = new File(["data"], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const fileList = [file] as unknown as FileList;
  input.dispatchEvent(new CustomEvent("change", { detail: { files: fileList } }));
  await vi.waitFor(() => {});
}

/** Simulate a UI5 select change event and mark option as selected. */
function selectUI5Option(select: Element, value: string) {
  const placeholder = select.querySelector("ui5-option[disabled]");
  placeholder?.removeAttribute("selected");
  const opt = Array.from(select.querySelectorAll("ui5-option")).find(
    (o) => o.getAttribute("value") === value,
  );
  opt?.setAttribute("selected", "");
  const fakeOption = { getAttribute: () => value, value };
  select.dispatchEvent(
    new CustomEvent("change", { detail: { selectedOption: fakeOption }, bubbles: true }),
  );
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

    // Verify sheet names are rendered as ui5-option elements
    const options = selector!.querySelectorAll("ui5-option:not([disabled])");
    expect(options.length).toBe(2);
    expect(options[0].getAttribute("value")).toBe("Sales");
    expect(options[1].getAttribute("value")).toBe("Expenses");
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

    const selector = contentEl.querySelector("[data-sheet-selector]")!;
    const select = selector.querySelector("ui5-select")!;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLElement;

    selectUI5Option(select, "Sales");
    confirmBtn.click();

    await vi.waitFor(() => {
      expect(orchestrator.importWithSheet).toHaveBeenCalledWith("Sales");
    });

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

    const selector = contentEl.querySelector("[data-sheet-selector]")!;
    const select = selector.querySelector("ui5-select")!;
    const confirmBtn = selector.querySelector(
      '[aria-label="Confirm sheet selection"]',
    ) as HTMLElement;

    selectUI5Option(select, "Sales");
    confirmBtn.click();

    await vi.waitFor(() => {
      expect(orchestrator.importWithSheet).toHaveBeenCalledWith("Sales");
    });

    expect(errorEl.textContent).toContain("Sheet 'Sales' is empty");
    expect(contentEl.querySelector("[data-sheet-selector]")).not.toBeNull();
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

    expect(contentEl.querySelector("[data-sheet-selector]")).not.toBeNull();

    const cancelBtn = contentEl.querySelector(
      '[aria-label="Cancel sheet selection"]',
    ) as HTMLElement;
    cancelBtn.click();

    expect(orchestrator.cancelPendingImport).toHaveBeenCalledOnce();
    expect(contentEl.querySelector("[data-sheet-selector]")).toBeNull();
    expect(errorEl.innerHTML).toBe("");
    const input = contentEl.querySelector(
      "ui5-file-uploader",
    ) as HTMLElement;
    expect((input as unknown as HTMLInputElement).value).toBe("");
  });
});
