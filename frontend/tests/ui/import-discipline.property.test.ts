// @vitest-environment node
import { describe, it, expect } from "vitest";
import fc from "fast-check";
import * as fs from "node:fs";
import * as path from "node:path";

// Feature: ui5-migration, Property 1: Side-effect import discipline

/**
 * Canonical mapping from UI5 custom element tag to the required side-effect import module path.
 * Every file that calls document.createElement("ui5-<tag>") must import the corresponding module.
 */
const TAG_TO_MODULE: Record<string, string> = {
  "ui5-message-strip": "@ui5/webcomponents/dist/MessageStrip.js",
  "ui5-button": "@ui5/webcomponents/dist/Button.js",
  "ui5-select": "@ui5/webcomponents/dist/Select.js",
  "ui5-option": "@ui5/webcomponents/dist/Option.js",
  "ui5-input": "@ui5/webcomponents/dist/Input.js",
  "ui5-label": "@ui5/webcomponents/dist/Label.js",
  "ui5-file-uploader": "@ui5/webcomponents/dist/FileUploader.js",
  "ui5-tabcontainer": "@ui5/webcomponents/dist/TabContainer.js",
  "ui5-tab": "@ui5/webcomponents/dist/Tab.js",
};

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

/** Parse a source file and return { tags: set of ui5 tags created, imports: set of import paths }. */
function parseFile(filePath: string): { tags: Set<string>; imports: Set<string> } {
  const content = fs.readFileSync(filePath, "utf-8");
  const tags = new Set<string>();
  const imports = new Set<string>();

  // Match document.createElement("ui5-*") calls
  const createRe = /document\.createElement\(\s*["']([^"']+)["']\s*\)/g;
  let m: RegExpExecArray | null;
  while ((m = createRe.exec(content)) !== null) {
    const tag = m[1];
    if (tag.startsWith("ui5-")) {
      tags.add(tag);
    }
  }

  // Match side-effect imports: import "..." or import '...'
  const importRe = /^\s*import\s+["']([^"']+)["']\s*;?/gm;
  while ((m = importRe.exec(content)) !== null) {
    imports.add(m[1]);
  }

  return { tags, imports };
}

/** Build test data: for each source file, the set of ui5 tags and their imports. */
const fileData = sourceFiles.map((fp) => ({
  relativePath: path.relative(UI_DIR, fp),
  ...parseFile(fp),
})).filter((f) => f.tags.size > 0);

describe("Property 1: Side-effect import discipline", () => {
  it("every file creating ui5-* elements has the corresponding side-effect import", () => {
    // **Validates: Requirements 1.4, 2.3, 3.4, 4.3, 5.7, 6.7, 7.9, 8.5, 9.3, 12.1, 12.2**
    fc.assert(
      fc.property(
        fc.constantFrom(...fileData),
        (file) => {
          for (const tag of file.tags) {
            const requiredModule = TAG_TO_MODULE[tag];
            expect(
              requiredModule,
              `Unknown UI5 tag "${tag}" in ${file.relativePath} — add it to TAG_TO_MODULE`,
            ).toBeDefined();
            expect(
              file.imports.has(requiredModule),
              `${file.relativePath} creates <${tag}> but is missing import "${requiredModule}"`,
            ).toBe(true);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("covers all source files in frontend/src/ui/ that use ui5 elements", () => {
    // Sanity: at least the known migrated files are detected
    const paths = fileData.map((f) => f.relativePath);
    expect(paths).toContain("components/error-banner.ts");
    expect(paths).toContain("components/header.ts");
    expect(paths).toContain("components/sheet-selector.ts");
    expect(paths).toContain("app.ts");
  });
});
