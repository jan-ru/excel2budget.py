/**
 * Documentation screen: build ApplicationContext and send to backend.
 * Display all 7 documentation artifacts.
 * Requirements: 5.1, 14.1, 14.4
 */

import type { ScreenContext } from "../app";
import { showError, clearError } from "../components/error-banner";
import { buildApplicationContext } from "../../pipeline/context-builder";
import { generateDocumentation } from "../../api/client";
import type { components } from "../../types/api";

type DocumentationPack = components["schemas"]["DocumentationPack"];

export async function render(ctx: ScreenContext): Promise<void> {
  const { contentEl, errorEl, orchestrator } = ctx;
  const { sourceData, transformResult, mappingConfig, template, userParams, generatedSql } = orchestrator;

  if (!sourceData || !transformResult || !mappingConfig || !template || !userParams || !generatedSql) {
    showError(errorEl, "Complete the full pipeline (upload → configure → transform) before generating documentation.");
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.style.cssText = "max-width:800px;margin:0 auto;";

  const heading = document.createElement("h2");
  heading.textContent = "Documentation";
  heading.style.cssText = "margin-bottom:16px;font-size:20px;font-weight:600;";
  wrapper.appendChild(heading);

  const status = document.createElement("p");
  status.textContent = "Generating documentation…";
  status.style.cssText = "color:#6b7280;font-size:14px;";
  wrapper.appendChild(status);
  contentEl.appendChild(wrapper);

  // Build ApplicationContext (metadata only, no raw financial data)
  const appCtx = buildApplicationContext(
    {
      sourceFileName: sourceData.metadata.sourceName || "budget.xlsx",
      packageName: template.packageName,
      templateName: template.templateName,
      userParams,
      configurationDate: new Date().toISOString(),
    },
    sourceData,
    transformResult,
    mappingConfig,
    template,
    generatedSql,
  );

  clearError(errorEl);
  const result = await generateDocumentation(appCtx);
  if (!result.ok) {
    status.textContent = "";
    showError(errorEl, `Documentation generation failed: ${result.error}`);
    return;
  }

  status.textContent = "";
  renderDocPack(wrapper, result.data);
}

function renderDocPack(container: HTMLElement, pack: DocumentationPack): void {
  const artifacts: { label: string; content: string | null }[] = [
    { label: "ArchiMate Diagram", content: pack.archimate?.renderedContent ?? null },
    { label: "BPMN Diagram", content: pack.bpmn?.renderedContent ?? null },
    { label: "Input Description", content: pack.inputDescription?.content ?? null },
    { label: "Output Description", content: pack.outputDescription?.content ?? null },
    { label: "Transform Description", content: pack.transformDescription?.content ?? null },
    { label: "Control Table", content: pack.controlTable ? formatControlTable(pack.controlTable) : null },
    { label: "User Instruction", content: pack.userInstruction?.content ?? null },
  ];

  for (const art of artifacts) {
    const section = document.createElement("details");
    section.style.cssText = "margin-bottom:12px;border:1px solid #e5e7eb;border-radius:6px;";
    section.open = true;

    const summary = document.createElement("summary");
    summary.textContent = art.label;
    summary.style.cssText = "padding:10px 14px;cursor:pointer;font-weight:500;background:#fafafa;border-radius:6px;";
    section.appendChild(summary);

    const body = document.createElement("div");
    body.style.cssText = "padding:12px 14px;white-space:pre-wrap;font-size:13px;font-family:monospace;";
    body.textContent = art.content ?? "(not generated)";
    section.appendChild(body);

    container.appendChild(section);
  }
}

function formatControlTable(ct: components["schemas"]["ControlTable"]): string {
  const t = ct.totals;
  const lines: string[] = [
    `Input rows: ${t.inputRowCount}`,
    `Output rows: ${t.outputRowCount}`,
    "",
    "Input totals:",
    ...t.inputTotals.map(n => `  ${n.label}: ${n.value}`),
    "",
    "Output totals:",
    ...t.outputTotals.map(n => `  ${n.label}: ${n.value}`),
    "",
    "Balance checks:",
    ...t.balanceChecks.map(b => `  ${b.description}: ${b.passed ? "PASS" : "FAIL"}`),
  ];
  return lines.join("\n");
}
