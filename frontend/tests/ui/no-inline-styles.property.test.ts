// @vitest-environment node
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as fs from "node:fs";
import * as path from "node:path";

// Feature: ui5-migration, Property 2: No inline styles on UI5 elements

/**
 * Scan source files for patterns where a ui5-* element is created and then
 * has inline styles applied via .style.cssText or .setAttribute("style", ...).
 *
 * The property: for any UI5 custom element created in the codebase, no inline
 * style attribute shall be set on that element. Only non-UI5 wrapper/layout
 * elements may have inline styles.
 */

/** Recursively collect all .ts files under a directory (excluding .d.ts). */
function collectTsFiles(dir: string): string[] {
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsFiles(full));
    } else if (entry.name.endsWith(".ts") && !entry.name.endsWith(".d.ts")) {
      results.push(full);
    }
  }
  return results;
}

const UI_DIR = path.resolve(__dirname, "../../src/ui");
const sourceFiles = collectTsFiles(UI_DIR);

interface Violation {
  file: string;
  variable: string;
  line: number;
  snippet: string;
}

/**
 * Parse a source file and detect any variable assigned from
 * document.createElement("ui5-*") that later has .style.cssText set
 * or .setAttribute("style", ...) called on it.
 */
function findInlineStyleViolations(filePath: string): Violation[] {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const violations: Violation[] = [];
  const relativePath = path.relative(UI_DIR, filePath);

  // Step 1: find all variable names assigned from createElement("ui5-*")
  // Patterns: const x = document.createElement("ui5-...") or let x = ...
  const ui5Vars = new Set<string>();
  const createRe = /(?:const|let|var)\s+(\w+)\s*=\s*document\.createElement\(\s*["']ui5-[^"']+["']\s*\)/g;
  let m: RegExpExecArray | null;
  while ((m = createRe.exec(content)) !== null) {
    ui5Vars.add(m[1]);
  }

  if (ui5Vars.size === 0) return violations;

  // Step 2: check if any of those variables have .style.cssText or .setAttribute("style"
  for (const varName of ui5Vars) {
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Check varName.style.cssText = ...
      if (line.includes(`${varName}.style.cssText`)) {
        violations.push({
          file: relativePath,
          variable: varName,
          line: i + 1,
          snippet: line.trim(),
        });
      }
      // Check varName.setAttribute("style", ...) or varName.setAttribute('style', ...)
      const setAttrRe = new RegExp(
        `${varName}\\.setAttribute\\(\\s*["']style["']`,
      );
      if (setAttrRe.test(line)) {
        violations.push({
          file: relativePath,
          variable: varName,
          line: i + 1,
          snippet: line.trim(),
        });
      }
    }
  }

  return violations;
}

/** Collect all violations across all source files. */
const allViolations = sourceFiles.flatMap(findInlineStyleViolations);

/** Collect file data for property-based iteration. */
const fileData = sourceFiles
  .map((fp) => ({
    relativePath: path.relative(UI_DIR, fp),
    fullPath: fp,
  }))
  .filter((f) => {
    const content = fs.readFileSync(f.fullPath, "utf-8");
    return /document\.createElement\(\s*["']ui5-/.test(content);
  });

describe("Property 2: No inline styles on UI5 elements", () => {
  it("no ui5-* element variable has .style.cssText or setAttribute('style') applied", () => {
    // **Validates: Requirements 1.5, 11.1**
    fc.assert(
      fc.property(
        fc.constantFrom(...fileData),
        (file) => {
          const violations = findInlineStyleViolations(file.fullPath);
          expect(
            violations,
            violations.length > 0
              ? `Inline style on UI5 element in ${file.relativePath}:\n` +
                violations
                  .map((v) => `  L${v.line} ${v.variable}: ${v.snippet}`)
                  .join("\n")
              : "",
          ).toHaveLength(0);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("aggregate: zero violations across all ui source files", () => {
    expect(
      allViolations,
      allViolations.length > 0
        ? `Found ${allViolations.length} inline style violation(s):\n` +
          allViolations
            .map((v) => `  ${v.file}:${v.line} ${v.variable}: ${v.snippet}`)
            .join("\n")
        : "",
    ).toHaveLength(0);
  });
});
