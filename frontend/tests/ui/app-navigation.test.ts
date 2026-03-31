// @vitest-environment jsdom
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { registerAllUI5Stubs } from "./helpers/ui5-stub";

// Mock all screen modules to avoid pulling in real dependencies
vi.mock("../../src/ui/screens/upload", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/screens/preview", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/screens/configuration", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/screens/transform", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/screens/output", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/screens/documentation", () => ({ render: vi.fn() }));
vi.mock("../../src/ui/components/header", () => ({
  createHeader: () => document.createElement("div"),
}));

import { mountApp } from "../../src/ui/app";

beforeAll(() => {
  registerAllUI5Stubs();
});

describe("App shell tab navigation", () => {
  let root: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  function getTabContainer(): HTMLElement {
    return root.querySelector("ui5-tabcontainer")!;
  }

  function getTabs(): HTMLElement[] {
    return Array.from(root.querySelectorAll("ui5-tab"));
  }

  it("renders 6 tabs with correct labels", () => {
    mountApp(root);
    const tabs = getTabs();
    expect(tabs).toHaveLength(6);

    const labels = tabs.map((t) => t.getAttribute("text"));
    expect(labels).toEqual([
      "Upload",
      "Preview",
      "Configuration",
      "Transform",
      "Output",
      "Documentation",
    ]);
  });

  it("initially selects the Upload tab", () => {
    mountApp(root);
    const tabs = getTabs();
    const selected = tabs.filter((t) => t.hasAttribute("selected"));
    expect(selected).toHaveLength(1);
    expect(selected[0].getAttribute("text")).toBe("Upload");
  });

  it("tab selection triggers navigation to the correct screen", async () => {
    mountApp(root);
    const tabContainer = getTabContainer();
    const tabs = getTabs();

    // Find the Configuration tab (index 2)
    const configTab = tabs.find((t) => t.getAttribute("text") === "Configuration")!;

    // Simulate UI5 tab-select event
    tabContainer.dispatchEvent(
      new CustomEvent("tab-select", {
        detail: { tab: configTab },
        bubbles: true,
      }),
    );

    // Wait for async navigate
    await new Promise((r) => setTimeout(r, 0));

    // The Configuration tab should now be selected
    expect(configTab.hasAttribute("selected")).toBe(true);

    // Upload tab should no longer be selected
    const uploadTab = tabs.find((t) => t.getAttribute("text") === "Upload")!;
    expect(uploadTab.hasAttribute("selected")).toBe(false);

    // The configuration screen render should have been called
    const configMod = await import("../../src/ui/screens/configuration");
    expect(configMod.render).toHaveBeenCalled();
  });

  it("each tab has a data-screen attribute matching the screen name", () => {
    mountApp(root);
    const tabs = getTabs();
    const screens = tabs.map((t) => t.dataset.screen);
    expect(screens).toEqual([
      "upload",
      "preview",
      "configuration",
      "transform",
      "output",
      "documentation",
    ]);
  });

  it("tab container has no inline style", () => {
    mountApp(root);
    const tabContainer = getTabContainer();
    expect(tabContainer.getAttribute("style")).toBeNull();
  });
});
