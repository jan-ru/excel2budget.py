/**
 * Configuration screen: package/template selection and user parameter inputs.
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 11.1, 13.2
 */

import "@ui5/webcomponents/dist/Select.js";
import "@ui5/webcomponents/dist/Option.js";
import "@ui5/webcomponents/dist/Input.js";
import "@ui5/webcomponents/dist/Label.js";
import "@ui5/webcomponents/dist/Button.js";

import type { ScreenContext } from "../app";
import { showError, clearError } from "../components/error-banner";
import { getPackages, getTemplates } from "../../api/client";

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator, navigate } = ctx;

  const form = document.createElement("div");
  form.style.cssText = "max-width:480px;margin:24px auto;";

  const heading = document.createElement("h2");
  heading.textContent = "Configuration";
  heading.style.cssText = "margin-bottom:16px;font-size:20px;font-weight:600;";
  form.appendChild(heading);

  // --- Package select ---
  const pkgLabel = document.createElement("ui5-label");
  pkgLabel.textContent = "Package";
  pkgLabel.setAttribute("for", "cfg-package");
  form.appendChild(pkgLabel);

  const pkgSelect = document.createElement("ui5-select");
  pkgSelect.id = "cfg-package";
  pkgSelect.setAttribute("aria-label", "Package");
  const pkgPlaceholder = document.createElement("ui5-option");
  pkgPlaceholder.setAttribute("value", "");
  pkgPlaceholder.textContent = "Loading\u2026";
  pkgPlaceholder.setAttribute("selected", "");
  pkgSelect.appendChild(pkgPlaceholder);
  form.appendChild(pkgSelect);

  // --- Template select ---
  const tplLabel = document.createElement("ui5-label");
  tplLabel.textContent = "Template";
  tplLabel.setAttribute("for", "cfg-template");
  form.appendChild(tplLabel);

  const tplSelect = document.createElement("ui5-select");
  tplSelect.id = "cfg-template";
  tplSelect.setAttribute("aria-label", "Template");
  tplSelect.setAttribute("disabled", "");
  const tplPlaceholder = document.createElement("ui5-option");
  tplPlaceholder.setAttribute("value", "");
  tplPlaceholder.textContent = "Select a package first";
  tplPlaceholder.setAttribute("selected", "");
  tplSelect.appendChild(tplPlaceholder);
  form.appendChild(tplSelect);

  // --- Budgetcode ---
  const bcLabel = document.createElement("ui5-label");
  bcLabel.textContent = "Budgetcode";
  bcLabel.setAttribute("for", "cfg-budgetcode");
  form.appendChild(bcLabel);

  const bcInput = document.createElement("ui5-input");
  bcInput.id = "cfg-budgetcode";
  bcInput.setAttribute("placeholder", "e.g. BC001");
  bcInput.setAttribute("aria-label", "Budgetcode");
  form.appendChild(bcInput);

  // --- Year ---
  const yrLabel = document.createElement("ui5-label");
  yrLabel.textContent = "Year";
  yrLabel.setAttribute("for", "cfg-year");
  form.appendChild(yrLabel);

  const yrInput = document.createElement("ui5-input");
  yrInput.id = "cfg-year";
  yrInput.setAttribute("type", "Number");
  yrInput.setAttribute("placeholder", String(new Date().getFullYear()));
  yrInput.setAttribute("aria-label", "Year");
  form.appendChild(yrInput);

  // --- Apply button ---
  const applyBtn = document.createElement("ui5-button");
  applyBtn.textContent = "Apply Configuration";
  applyBtn.setAttribute("design", "Emphasized");
  form.appendChild(applyBtn);

  contentEl.appendChild(form);

  // --- Load packages ---
  const pkgResult = await getPackages();
  if (!pkgResult.ok) {
    showError(errorEl, `Failed to load packages: ${pkgResult.error}`);
    return;
  }
  pkgSelect.innerHTML = "";
  const pkgDefaultOpt = document.createElement("ui5-option");
  pkgDefaultOpt.setAttribute("value", "");
  pkgDefaultOpt.textContent = "Select package\u2026";
  pkgDefaultOpt.setAttribute("selected", "");
  pkgSelect.appendChild(pkgDefaultOpt);
  for (const p of pkgResult.data) {
    const opt = document.createElement("ui5-option");
    opt.setAttribute("value", p);
    opt.textContent = p;
    pkgSelect.appendChild(opt);
  }

  // --- On package change, load templates ---
  pkgSelect.addEventListener("change", async (e: Event) => {
    const selectedOption = (e as CustomEvent).detail?.selectedOption;
    const pkg = selectedOption?.getAttribute?.("value") ?? selectedOption?.value ?? "";
    tplSelect.innerHTML = "";
    const loadingOpt = document.createElement("ui5-option");
    loadingOpt.setAttribute("value", "");
    loadingOpt.textContent = "Loading\u2026";
    loadingOpt.setAttribute("selected", "");
    tplSelect.appendChild(loadingOpt);
    tplSelect.setAttribute("disabled", "");
    if (!pkg) return;

    const tplResult = await getTemplates(pkg);
    if (!tplResult.ok) {
      showError(errorEl, `Failed to load templates: ${tplResult.error}`);
      return;
    }
    tplSelect.innerHTML = "";
    const tplDefaultOpt = document.createElement("ui5-option");
    tplDefaultOpt.setAttribute("value", "");
    tplDefaultOpt.textContent = "Select template\u2026";
    tplDefaultOpt.setAttribute("selected", "");
    tplSelect.appendChild(tplDefaultOpt);
    for (const t of tplResult.data) {
      const opt = document.createElement("ui5-option");
      opt.setAttribute("value", t);
      opt.textContent = t;
      tplSelect.appendChild(opt);
    }
    tplSelect.removeAttribute("disabled");
  });

  // --- Helper to read selected value from ui5-select ---
  function getSelectValue(select: HTMLElement): string {
    const selected = select.querySelector("ui5-option[selected]:not([disabled])") as HTMLElement | null;
    return selected?.getAttribute("value") ?? "";
  }

  // --- Apply ---
  applyBtn.addEventListener("click", async () => {
    clearError(errorEl);

    // Reset value states
    pkgSelect.setAttribute("value-state", "None");
    tplSelect.setAttribute("value-state", "None");
    bcInput.setAttribute("value-state", "None");
    yrInput.setAttribute("value-state", "None");

    const pkg = getSelectValue(pkgSelect);
    const tpl = getSelectValue(tplSelect);
    const bc = (bcInput.getAttribute("value") ?? "").trim();
    const yr = parseInt(yrInput.getAttribute("value") ?? "", 10);

    let hasError = false;

    if (!pkg) {
      pkgSelect.setAttribute("value-state", "Negative");
      hasError = true;
    }
    if (!tpl) {
      tplSelect.setAttribute("value-state", "Negative");
      hasError = true;
    }
    if (!bc) {
      bcInput.setAttribute("value-state", "Negative");
      hasError = true;
    }
    if (!yr || yr <= 0) {
      yrInput.setAttribute("value-state", "Negative");
      hasError = true;
    }

    if (hasError) {
      if (!pkg || !tpl) {
        showError(errorEl, "Please select a package and template.");
      } else if (!bc) {
        showError(errorEl, "Budgetcode is required.");
      } else {
        showError(errorEl, "Year must be a positive number.");
      }
      return;
    }

    const tplResult = await orchestrator.selectTemplate(pkg, tpl);
    if (!tplResult.ok) {
      showError(errorEl, tplResult.error);
      return;
    }
    orchestrator.setParams(bc, yr);
    navigate("transform");
  });
}
