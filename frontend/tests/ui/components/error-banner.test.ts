/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeAll } from "vitest";
import fc from "fast-check";
import { showError, clearError } from "../../../src/ui/components/error-banner";
import { registerAllUI5Stubs } from "../helpers/ui5-stub";

beforeAll(() => {
  registerAllUI5Stubs();
});

// Feature: ui5-migration, Property 3: showError renders a correct message strip
describe("Property 3: showError renders a correct message strip", () => {
  it("renders a ui5-message-strip with design=Negative, role=alert, and correct text", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 200 }),
        (message) => {
          const container = document.createElement("div");
          showError(container, message);

          const strip = container.querySelector("ui5-message-strip");
          expect(strip).not.toBeNull();
          expect(strip!.getAttribute("design")).toBe("Negative");
          expect(strip!.getAttribute("role")).toBe("alert");
          expect(strip!.textContent).toBe(message);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("replaces previous content in the container", () => {
    const container = document.createElement("div");
    container.innerHTML = "<p>old content</p>";

    showError(container, "new error");

    expect(container.children.length).toBe(1);
    expect(container.querySelector("ui5-message-strip")).not.toBeNull();
    expect(container.querySelector("p")).toBeNull();
  });
});

// Feature: ui5-migration, Property 4: showError/clearError round trip
describe("Property 4: showError/clearError round trip", () => {
  it("container is empty after showError followed by clearError", () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 200 }),
        (message) => {
          const container = document.createElement("div");
          showError(container, message);
          expect(container.children.length).toBe(1);

          clearError(container);
          expect(container.children.length).toBe(0);
          expect(container.innerHTML).toBe("");
        },
      ),
      { numRuns: 100 },
    );
  });

  it("clearError on already-empty container is a no-op", () => {
    const container = document.createElement("div");
    clearError(container);
    expect(container.children.length).toBe(0);
  });
});
