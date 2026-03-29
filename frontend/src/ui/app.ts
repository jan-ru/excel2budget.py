/**
 * Application shell and screen router.
 *
 * Screen-based navigation: Upload, Preview, Configuration, Transform, Output, Documentation.
 * Plain TypeScript + @ui5/webcomponents.
 *
 * Requirements: 14.1
 */

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

  const nav = document.createElement("nav");
  nav.setAttribute("role", "navigation");
  nav.setAttribute("aria-label", "Main navigation");
  nav.style.cssText =
    "display:flex;gap:0;border-bottom:1px solid #e5e7eb;background:#fafafa;";

  const navButtons: Record<string, HTMLButtonElement> = {};
  for (const name of Object.keys(SCREEN_LABELS) as ScreenName[]) {
    const btn = document.createElement("button");
    btn.textContent = SCREEN_LABELS[name];
    btn.dataset.screen = name;
    btn.style.cssText =
      "padding:10px 18px;border:none;background:transparent;cursor:pointer;font-size:14px;border-bottom:2px solid transparent;";
    btn.addEventListener("click", () => navigate(name));
    navButtons[name] = btn;
    nav.appendChild(btn);
  }

  const errorEl = document.createElement("div");
  errorEl.id = "app-error";

  const contentEl = document.createElement("div");
  contentEl.id = "app-content";
  contentEl.style.cssText = "flex:1;overflow:auto;padding:16px;";

  root.appendChild(header);
  root.appendChild(nav);
  root.appendChild(errorEl);
  root.appendChild(contentEl);

  function updateNavHighlight(): void {
    for (const [name, btn] of Object.entries(navButtons)) {
      const active = name === currentScreen;
      btn.style.borderBottomColor = active ? "#2563eb" : "transparent";
      btn.style.fontWeight = active ? "600" : "400";
      btn.style.color = active ? "#2563eb" : "#374151";
    }
  }

  async function navigate(screen: ScreenName): Promise<void> {
    currentScreen = screen;
    getPdfOptions = () => null;
    updateNavHighlight();
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
