// @vitest-environment jsdom
// Feature: ui5-migration, Property 8: Configuration select options match data
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

describe("Property 8: Configuration select options match data", () => {
  it("package select contains one ui5-option per package name", async () => {
    // **Validates: Requirements 7.1, 7.2**
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.string({ minLength: 1, maxLength: 30 }), { minLength: 1, maxLength: 20 }),
        async (packages) => {
          (getPackages as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: packages });
          (getTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: [] });

          const { ctx, contentEl } = createCtx();
          await render(ctx);

          const pkgSelect = contentEl.querySelector("#cfg-package") as HTMLElement;
          expect(pkgSelect).not.toBeNull();

          const allOptions = Array.from(pkgSelect.querySelectorAll("ui5-option"));
          // First option is the placeholder with value=""
          const placeholder = allOptions[0];
          expect(placeholder.getAttribute("value")).toBe("");

          const pkgOptions = allOptions.slice(1);
          expect(pkgOptions).toHaveLength(packages.length);

          for (let i = 0; i < packages.length; i++) {
            expect(pkgOptions[i].getAttribute("value")).toBe(packages[i]);
            expect(pkgOptions[i].textContent).toBe(packages[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("template select contains one ui5-option per template name after package selection", async () => {
    // **Validates: Requirements 7.1, 7.2**
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.string({ minLength: 1, maxLength: 30 }), { minLength: 1, maxLength: 20 }),
        fc.array(fc.string({ minLength: 1, maxLength: 30 }), { minLength: 1, maxLength: 20 }),
        async (packages, templates) => {
          (getPackages as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: packages });
          (getTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: templates });

          const { ctx, contentEl } = createCtx();
          await render(ctx);

          if (packages.length === 0) return;

          // Simulate selecting the first package
          const pkgSelect = contentEl.querySelector("#cfg-package") as HTMLElement;
          const firstPkgValue = packages[0];
          const fakeOption = { getAttribute: () => firstPkgValue, value: firstPkgValue };

          // Dispatch change event and await the async handler
          const changeEvent = new CustomEvent("change", {
            detail: { selectedOption: fakeOption },
            bubbles: true,
          });

          // The change handler is async — we need to wait for it
          pkgSelect.dispatchEvent(changeEvent);
          // Allow the async handler to resolve
          await vi.waitFor(() => {
            expect(getTemplates).toHaveBeenCalledWith(firstPkgValue);
          });

          const tplSelect = contentEl.querySelector("#cfg-template") as HTMLElement;
          expect(tplSelect).not.toBeNull();

          const allOptions = Array.from(tplSelect.querySelectorAll("ui5-option"));
          // First option is the placeholder with value=""
          const placeholder = allOptions[0];
          expect(placeholder.getAttribute("value")).toBe("");

          const tplOptions = allOptions.slice(1);
          expect(tplOptions).toHaveLength(templates.length);

          for (let i = 0; i < templates.length; i++) {
            expect(tplOptions[i].getAttribute("value")).toBe(templates[i]);
            expect(tplOptions[i].textContent).toBe(templates[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
