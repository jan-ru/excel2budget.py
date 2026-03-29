import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { sanitizeCellValue } from "../../src/security/xss-sanitizer";

describe("Property 12: XSS Sanitization", () => {
  it("output contains no HTML tags", () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = sanitizeCellValue(input);
        // No raw < followed by tag-like content and closed with >
        expect(result).not.toMatch(/<[a-zA-Z/][^>]*>/);
      }),
      { numRuns: 100 },
    );
  });

  it("output contains no javascript: URIs", () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = sanitizeCellValue(input);
        expect(result.toLowerCase()).not.toMatch(/javascript\s*:/);
      }),
      { numRuns: 100 },
    );
  });

  it("output contains no vbscript: URIs", () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = sanitizeCellValue(input);
        expect(result.toLowerCase()).not.toMatch(/vbscript\s*:/);
      }),
      { numRuns: 100 },
    );
  });

  it("output contains no on-event handler attributes", () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = sanitizeCellValue(input);
        expect(result).not.toMatch(/on\w+\s*=\s*["'][^"']*["']/i);
      }),
      { numRuns: 100 },
    );
  });

  it("output contains no script elements", () => {
    fc.assert(
      fc.property(fc.string(), (input) => {
        const result = sanitizeCellValue(input);
        expect(result.toLowerCase()).not.toMatch(/<\s*script/);
      }),
      { numRuns: 100 },
    );
  });

  it("strips known XSS payloads", () => {
    const payloads = [
      '<script>alert("xss")</script>',
      '<img src=x onerror="alert(1)">',
      '<a href="javascript:alert(1)">click</a>',
      '<div onmouseover="steal()">hover</div>',
      '<style>body{background:url("javascript:alert(1)")}</style>',
      'javascript:alert(document.cookie)',
      'vbscript:MsgBox("xss")',
      '<SCRIPT SRC=https://evil.com/xss.js></SCRIPT>',
      '<img src="x" ONERROR="alert(1)">',
      'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
      'expression(alert(1))',
    ];

    for (const payload of payloads) {
      const result = sanitizeCellValue(payload);
      expect(result).not.toMatch(/<\s*script/i);
      expect(result.toLowerCase()).not.toMatch(/javascript\s*:/);
      expect(result.toLowerCase()).not.toMatch(/vbscript\s*:/);
      expect(result).not.toMatch(/on\w+\s*=\s*["'][^"']*["']/i);
      expect(result).not.toMatch(/<[a-zA-Z/][^>]*>/);
    }
  });

  it("preserves plain text content", () => {
    fc.assert(
      fc.property(
        fc.stringOf(fc.constantFrom(..."abcdefghijklmnopqrstuvwxyz0123456789 ")),
        (input) => {
          const result = sanitizeCellValue(input);
          // Plain alphanumeric + space text should survive (unchanged)
          expect(result).toBe(input);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("returns empty/falsy values unchanged", () => {
    expect(sanitizeCellValue("")).toBe("");
  });
});
