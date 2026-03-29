/**
 * Configuration screen: package/template selection and user parameter inputs.
 * Requirements: 14.1, 14.3
 */

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
  const pkgLabel = label("Package");
  const pkgSelect = document.createElement("select");
  pkgSelect.setAttribute("aria-label", "Package");
  pkgSelect.style.cssText = selectStyle();
  pkgSelect.innerHTML = '<option value="">Loading…</option>';
  form.appendChild(pkgLabel);
  form.appendChild(pkgSelect);

  // --- Template select ---
  const tplLabel = label("Template");
  const tplSelect = document.createElement("select");
  tplSelect.setAttribute("aria-label", "Template");
  tplSelect.style.cssText = selectStyle();
  tplSelect.disabled = true;
  tplSelect.innerHTML = '<option value="">Select a package first</option>';
  form.appendChild(tplLabel);
  form.appendChild(tplSelect);

  // --- Budgetcode ---
  const bcLabel = label("Budgetcode");
  const bcInput = document.createElement("input");
  bcInput.type = "text";
  bcInput.placeholder = "e.g. BC001";
  bcInput.setAttribute("aria-label", "Budgetcode");
  bcInput.style.cssText = inputStyle();
  form.appendChild(bcLabel);
  form.appendChild(bcInput);

  // --- Year ---
  const yrLabel = label("Year");
  const yrInput = document.createElement("input");
  yrInput.type = "number";
  yrInput.placeholder = String(new Date().getFullYear());
  yrInput.setAttribute("aria-label", "Year");
  yrInput.style.cssText = inputStyle();
  form.appendChild(yrLabel);
  form.appendChild(yrInput);

  // --- Apply button ---
  const applyBtn = document.createElement("button");
  applyBtn.textContent = "Apply Configuration";
  applyBtn.style.cssText =
    "margin-top:16px;padding:10px 20px;background:#2563eb;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;width:100%;";
  form.appendChild(applyBtn);

  contentEl.appendChild(form);

  // --- Load packages ---
  const pkgResult = await getPackages();
  if (!pkgResult.ok) {
    showError(errorEl, `Failed to load packages: ${pkgResult.error}`);
    return;
  }
  pkgSelect.innerHTML = '<option value="">Select package…</option>';
  for (const p of pkgResult.data) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    pkgSelect.appendChild(opt);
  }

  // --- On package change, load templates ---
  pkgSelect.addEventListener("change", async () => {
    const pkg = pkgSelect.value;
    tplSelect.innerHTML = '<option value="">Loading…</option>';
    tplSelect.disabled = true;
    if (!pkg) return;

    const tplResult = await getTemplates(pkg);
    if (!tplResult.ok) {
      showError(errorEl, `Failed to load templates: ${tplResult.error}`);
      return;
    }
    tplSelect.innerHTML = '<option value="">Select template…</option>';
    for (const t of tplResult.data) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      tplSelect.appendChild(opt);
    }
    tplSelect.disabled = false;
  });

  // --- Apply ---
  applyBtn.addEventListener("click", async () => {
    clearError(errorEl);
    const pkg = pkgSelect.value;
    const tpl = tplSelect.value;
    const bc = bcInput.value.trim();
    const yr = parseInt(yrInput.value, 10);

    if (!pkg || !tpl) {
      showError(errorEl, "Please select a package and template.");
      return;
    }
    if (!bc) {
      showError(errorEl, "Budgetcode is required.");
      return;
    }
    if (!yr || yr <= 0) {
      showError(errorEl, "Year must be a positive number.");
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

// --- Helpers ---
function label(text: string): HTMLElement {
  const el = document.createElement("label");
  el.textContent = text;
  el.style.cssText = "display:block;margin-top:12px;margin-bottom:4px;font-size:13px;font-weight:500;color:#374151;";
  return el;
}
function selectStyle(): string {
  return "width:100%;padding:8px;border:1px solid #d1d5db;border-radius:4px;font-size:14px;";
}
function inputStyle(): string {
  return "width:100%;padding:8px;border:1px solid #d1d5db;border-radius:4px;font-size:14px;box-sizing:border-box;";
}
