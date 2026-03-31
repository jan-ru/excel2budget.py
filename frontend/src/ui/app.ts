/**
 * Application shell and screen router.
 *
 * Screen-based navigation: Upload, Preview, Configuration, Transform, Output, Documentation.
 * Plain TypeScript + @ui5/webcomponents.
 *
 * Requirements: 14.1
 */

import "@ui5/webcomponents/dist/TabContainer.js";
import "@ui5/webcomponents/dist/Tab.js";

import { PipelineOrchestrator } from "../pipeline/orchestrator";
import { createHeader } from "./components/header";
import type { PDFExportOptions } from "../export/pdf-exporter";

// --- Screen type ---
export type ScreenName =
  | "upload"
  | "preview"
  | "configuration"
  | "transform"
  | "output"
  | "documentation";

export interface ScreenContext {
  orchestrator: PipelineOrchestrator;
  navigate: (screen: ScreenName) => void;
  contentEl: HTMLElement;
  errorEl: HTMLElement;
  /** Current screen's PDF options provider (set by each screen). */
  getPdfOptions: () => PDFExportOptions | null;
}

type ScreenRenderer = (ctx: ScreenContext) => void | Promise<void>;
interface ScreenModule { render: ScreenRenderer }

// --- Screen module imports (static, tree-shaken by Vite) ---
import * as uploadScreen from "./screens/upload";
import * as previewScreen from "./screens/preview";
import * as configurationScreen from "./screens/configuration";
import * as transformScreen from "./screens/transform";
import * as outputScreen from "./screens/output";
import * as documentationScreen from "./screens/documentation";

const SCREEN_MODULES: Record<ScreenName, ScreenModule> = {
  upload: uploadScreen,
  preview: previewScreen,
  configuration: configurationScreen,
  transform: transformScreen,
  output: outputScreen,
  documentation: documentationScreen,
};

const SCREEN_LABELS: Record<ScreenName, string> = {
  upload: "Upload",
  preview: "Preview",
  configuration: "Configuration",
  transform: "Transform",
  output: "Output",
  documentation: "Documentation",
};

/** Mount the application into the given root element. */
export function mountApp(root: HTMLElement): void {
  const orchestrator = new PipelineOrchestrator();
  let currentScreen: ScreenName = "upload";
  let getPdfOptions: () => PDFExportOptions | null = () => null;

  // --- Layout ---
  root.innerHTML = "";
  root.style.cssText = "display:flex;flex-direction:column;height:100vh;font-family:sans-serif;";

  const header = createHeader({ getPdfOptions: () => getPdfOptions() });

  const tabContainer = document.createElement("ui5-tabcontainer");
  tabContainer.setAttribute("fixed", "");

  const tabs: Record<string, HTMLElement> = {};
  for (const name of Object.keys(SCREEN_LABELS) as ScreenName[]) {
    const tab = document.createElement("ui5-tab");
    tab.setAttribute("text", SCREEN_LABELS[name]);
    tab.dataset.screen = name;
    if (name === currentScreen) {
      tab.setAttribute("selected", "");
    }
    tabs[name] = tab;
    tabContainer.appendChild(tab);
  }

  tabContainer.addEventListener("tab-select", (e) => {
    const selectedTab = (e as CustomEvent).detail.tab as HTMLElement;
    const screen = selectedTab.dataset.screen as ScreenName | undefined;
    if (screen) navigate(screen);
  });

  const errorEl = document.createElement("div");
  errorEl.id = "app-error";

  const contentEl = document.createElement("div");
  contentEl.id = "app-content";
  contentEl.style.cssText = "flex:1;overflow:auto;padding:16px;";

  root.appendChild(header);
  root.appendChild(tabContainer);
  root.appendChild(errorEl);
  root.appendChild(contentEl);

  async function navigate(screen: ScreenName): Promise<void> {
    currentScreen = screen;
    getPdfOptions = () => null;
    // Update tab selection — UI5 handles active styling
    for (const [name, tab] of Object.entries(tabs)) {
      if (name === screen) {
        tab.setAttribute("selected", "");
      } else {
        tab.removeAttribute("selected");
      }
    }
    contentEl.innerHTML = "";
    errorEl.innerHTML = "";

    const ctx: ScreenContext = {
      orchestrator,
      navigate,
      contentEl,
      errorEl,
      get getPdfOptions() { return getPdfOptions; },
      set getPdfOptions(fn: () => PDFExportOptions | null) { getPdfOptions = fn; },
    };

    try {
      const mod = SCREEN_MODULES[screen];
      await mod.render(ctx);
    } catch (err) {
      contentEl.textContent = `Failed to load screen: ${(err as Error).message}`;
    }
  }

  // Initial render
  navigate("upload");
}
