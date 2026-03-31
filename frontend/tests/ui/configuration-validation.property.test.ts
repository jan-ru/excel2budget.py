// @vitest-environment jsdom
// Feature: ui5-migration, Property 9: Configuration validation sets Negative value-state
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import fc from "fast-check";
import type { ScreenContext } from "../../src/ui/app";
import type { PipelineOrchestrator } from "../../src/pipeline/orchestrator";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

vi.mock("../../src/api/client", () => ({
  getPackages: vi.fn(),
  getTemplates: vi.fn(),
}));

import { getPackages, getTemplates } from "../../src/api/client";
import { render } from "../../src/ui/screens/configuration";

beforeAll(() => {
  registerAllUI5Stubs();
});

function createCtx() {
  const contentEl = document.createElement("div");
  const errorEl = document.createElement("div");
  const navigate = vi.fn();
  const orchestrator = {
    selectTemplate: vi.fn(),
    setParams: vi.fn(),
  } as unknown as PipelineOrchestrator;
  const ctx: ScreenContext = { contentEl, errorEl, orchestrator, navigate, getPdfOptions: () => null };
  return { ctx, contentEl, errorEl };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Property 9: Configuration validation sets Negative value-state", () => {
  it("invalid fields get value-state Negative, valid fields get None", async () => {
    // **Validates: Requirements 7.6, 7.7, 7.8**
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          hasPackage: fc.boolean(),
          hasTemplate: fc.boolean(),
          hasBudgetcode: fc.boolean(),
          hasValidYear: fc.boolean(),
        }),
        async ({ hasPackage, hasTemplate, hasBudgetcode, hasValidYear }) => {
          // Skip the all-valid case — validation won't trigger value-state changes
          // because the code navigates away on success
          if (hasPackage && hasTemplate && hasBudgetcode && hasValidYear) return;

          const testPackages = ["PKG-A", "PKG-B"];
          const testTemplates = ["TPL-X", "TPL-Y"];

          (getPackages as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: testPackages });
          (getTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: testTemplates });

          const { ctx, contentEl } = createCtx();
          await render(ctx);

          const pkgSelect = contentEl.querySelector("#cfg-package") as HTMLElement;
          const tplSelect = contentEl.querySelector("#cfg-template") as HTMLElement;
          const bcInput = contentEl.querySelector("#cfg-budgetcode") as HTMLElement;
          const yrInput = contentEl.querySelector("#cfg-year") as HTMLElement;
          const applyBtn = contentEl.querySelector("ui5-button") as HTMLElement;

          // Set up package selection
          if (hasPackage) {
            // Remove selected from placeholder, set selected on a real package option
            const placeholder = pkgSelect.querySelector('ui5-option[value=""]');
            if (placeholder) placeholder.removeAttribute("selected");
            const pkgOpt = pkgSelect.querySelector('ui5-option[value="PKG-A"]');
            if (pkgOpt) pkgOpt.setAttribute("selected", "");
          }

          // Set up template selection
          if (hasTemplate) {
            // First load templates by simulating package change
            const fakeOption = { getAttribute: () => "PKG-A", value: "PKG-A" };
            const changeEvent = new CustomEvent("change", {
              detail: { selectedOption: fakeOption },
              bubbles: true,
            });
            pkgSelect.dispatchEvent(changeEvent);
            await vi.waitFor(() => {
              expect(getTemplates).toHaveBeenCalledWith("PKG-A");
            });

            // Now select a template
            const tplPlaceholder = tplSelect.querySelector('ui5-option[value=""]');
            if (tplPlaceholder) tplPlaceholder.removeAttribute("selected");
            const tplOpt = tplSelect.querySelector('ui5-option[value="TPL-X"]');
            if (tplOpt) tplOpt.setAttribute("selected", "");
          }

          // Set up budgetcode
          if (hasBudgetcode) {
            bcInput.setAttribute("value", "BC001");
          }

          // Set up year
          if (hasValidYear) {
            yrInput.setAttribute("value", "2025");
          }

          // Click Apply
          applyBtn.click();

          // Verify value-state on each field
          const expectedPkgState = hasPackage ? "None" : "Negative";
          const expectedTplState = hasTemplate ? "None" : "Negative";
          const expectedBcState = hasBudgetcode ? "None" : "Negative";
          const expectedYrState = hasValidYear ? "None" : "Negative";

          expect(pkgSelect.getAttribute("value-state")).toBe(expectedPkgState);
          expect(tplSelect.getAttribute("value-state")).toBe(expectedTplState);
          expect(bcInput.getAttribute("value-state")).toBe(expectedBcState);
          expect(yrInput.getAttribute("value-state")).toBe(expectedYrState);
        },
      ),
      { numRuns: 100 },
    );
  });
});
