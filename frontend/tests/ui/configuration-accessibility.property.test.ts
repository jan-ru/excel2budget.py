// @vitest-environment jsdom
// Feature: ui5-migration, Property 10: Label-for-input accessibility pairing
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

describe("Property 10: Label-for-input accessibility pairing", () => {
  it("every ui5-label for attribute references an existing ui5-input or ui5-select id", async () => {
    // **Validates: Requirements 7.10**
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 10 }),
        async (packages) => {
          (getPackages as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: packages });
          (getTemplates as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true, data: [] });

          const { ctx, contentEl } = createCtx();
          await render(ctx);

          const labels = Array.from(contentEl.querySelectorAll("ui5-label"));

          // The configuration screen must have labels
          expect(labels.length).toBeGreaterThan(0);

          for (const label of labels) {
            const forAttr = label.getAttribute("for");
            // Every label must have a for attribute
            expect(forAttr).toBeTruthy();

            // The for value must reference an existing ui5-input or ui5-select in the form
            const target =
              contentEl.querySelector(`ui5-input#${forAttr}`) ??
              contentEl.querySelector(`ui5-select#${forAttr}`);
            expect(target).not.toBeNull();
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
