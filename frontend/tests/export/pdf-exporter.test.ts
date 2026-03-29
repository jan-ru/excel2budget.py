import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { generatePdf } from "../../src/export/pdf-exporter";
import type { PDFExportOptions } from "../../src/export/pdf-exporter";
import type { components } from "../../src/types/api";

type ScreenContentType = components["schemas"]["ScreenContentType"];

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Non-empty printable ASCII string (avoids encoding edge cases in PDF text). */
const arbPrintable = fc.stringOf(
  fc.constantFrom(..."abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"),
  { minLength: 1, maxLength: 30 },
);

const arbContentType: fc.Arbitrary<ScreenContentType> = fc.constantFrom(
  "SPREADSHEET" as const,
  "DIAGRAM" as const,
  "CONTROL_TABLE" as const,
);

const arbPdfOptions: fc.Arbitrary<PDFExportOptions> = fc
  .record({
    screenTitle: arbPrintable,
    configurationName: arbPrintable,
    packageName: arbPrintable,
    templateName: arbPrintable,
    contentType: arbContentType,
    textContent: arbPrintable,
  })
  .map(({ screenTitle, configurationName, packageName, templateName, contentType, textContent }) => ({
    metadata: {
      screenTitle,
      configurationName,
      packageName,
      templateName,
      generatedAt: new Date().toISOString(),
    },
    content: {
      contentType,
      textContent,
    },
  }));

// ---------------------------------------------------------------------------
// Property Tests
// ---------------------------------------------------------------------------

describe("Property 14: PDF Generation with Metadata", () => {
  it("output is non-empty and starts with %PDF", async () => {
    await fc.assert(
      fc.asyncProperty(arbPdfOptions, async (options) => {
        const bytes = await generatePdf(options);
        expect(bytes.byteLength).toBeGreaterThan(0);
        // PDF magic bytes: %PDF
        const header = new TextDecoder().decode(new Uint8Array(bytes).slice(0, 5));
        expect(header).toMatch(/^%PDF-/);
      }),
      { numRuns: 20 },
    );
  });

  it("PDF content contains screenTitle", async () => {
    await fc.assert(
      fc.asyncProperty(arbPdfOptions, async (options) => {
        const bytes = await generatePdf(options);
        const text = new TextDecoder("latin1").decode(new Uint8Array(bytes));
        expect(text).toContain(options.metadata.screenTitle);
      }),
      { numRuns: 20 },
    );
  });

  it("PDF content contains configurationName", async () => {
    await fc.assert(
      fc.asyncProperty(arbPdfOptions, async (options) => {
        const bytes = await generatePdf(options);
        const text = new TextDecoder("latin1").decode(new Uint8Array(bytes));
        expect(text).toContain(options.metadata.configurationName);
      }),
      { numRuns: 20 },
    );
  });

  it("PDF content contains packageName", async () => {
    await fc.assert(
      fc.asyncProperty(arbPdfOptions, async (options) => {
        const bytes = await generatePdf(options);
        const text = new TextDecoder("latin1").decode(new Uint8Array(bytes));
        expect(text).toContain(options.metadata.packageName);
      }),
      { numRuns: 20 },
    );
  });

  it("PDF content contains templateName", async () => {
    await fc.assert(
      fc.asyncProperty(arbPdfOptions, async (options) => {
        const bytes = await generatePdf(options);
        const text = new TextDecoder("latin1").decode(new Uint8Array(bytes));
        expect(text).toContain(options.metadata.templateName);
      }),
      { numRuns: 20 },
    );
  });

  it("supports all three screen content types", async () => {
    const contentTypes: ScreenContentType[] = ["SPREADSHEET", "DIAGRAM", "CONTROL_TABLE"];
    for (const ct of contentTypes) {
      const bytes = await generatePdf({
        metadata: {
          screenTitle: "Test",
          configurationName: "cfg",
          packageName: "pkg",
          templateName: "tpl",
          generatedAt: "2025-01-01T00:00:00Z",
        },
        content: {
          contentType: ct,
          textContent: "Sample content for " + ct,
        },
      });
      const header = new TextDecoder().decode(new Uint8Array(bytes).slice(0, 5));
      expect(header).toMatch(/^%PDF-/);
    }
  });
});
