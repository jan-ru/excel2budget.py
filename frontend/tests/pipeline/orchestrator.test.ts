/**
 * Property test: Pipeline Halt on Failure (Property 16)
 *
 * If step N fails, no step after N executes, and the pipeline returns
 * an error describing the failure at step N.
 *
 * Feature: frontend-backend-split, Property 16: Pipeline Halt on Failure
 * Validates: Requirements 13.3
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import fc from "fast-check";
import type { PipelineStep } from "../../src/pipeline/orchestrator";

// --- Mock all dependencies before importing the orchestrator ---

vi.mock("../../src/guards/memory-guard", () => ({
  validateFileSize: vi.fn(),
}));

vi.mock("../../src/import/excel-importer", () => ({
  parseExcelFile: vi.fn(),
  extractBudgetData: vi.fn(),
  extractMappingConfig: vi.fn(),
  scanForHeaderRow: vi.fn(),
  getSheetNames: vi.fn((wb: any) => wb?.SheetNames ?? []),
  hasSheet: vi.fn((wb: any, name: string) => (wb?.SheetNames ?? []).includes(name)),
  ParseError: class ParseError extends Error {
    constructor(msg: string) { super(msg); this.name = "ParseError"; }
  },
  MappingError: class MappingError extends Error {
    constructor(msg: string) { super(msg); this.name = "MappingError"; }
  },
}));

vi.mock("../../src/validation/data-validator", () => ({
  validateMappingConfig: vi.fn(),
  validateUserParams: vi.fn(),
  validateDCValues: vi.fn(),
}));

vi.mock("../../src/api/client", () => ({
  getTemplate: vi.fn(),
}));

vi.mock("../../src/transform/sql-generator", () => ({
  generateTransformSql: vi.fn(),
  SQLGenerationError: class SQLGenerationError extends Error {
    constructor(msg: string) { super(msg); this.name = "SQLGenerationError"; }
  },
}));

vi.mock("../../src/engine/duckdb-engine", () => ({
  initialize: vi.fn(),
  registerTable: vi.fn(),
  executeSql: vi.fn(),
}));

import { PipelineOrchestrator } from "../../src/pipeline/orchestrator";
import { validateFileSize } from "../../src/guards/memory-guard";
import {
  parseExcelFile,
  extractBudgetData,
  extractMappingConfig,
  scanForHeaderRow,
  ParseError,
  MappingError,
} from "../../src/import/excel-importer";
import {
  validateMappingConfig,
  validateUserParams,
  validateDCValues,
} from "../../src/validation/data-validator";
import { getTemplate } from "../../src/api/client";
import { generateTransformSql } from "../../src/transform/sql-generator";
import * as duckdb from "../../src/engine/duckdb-engine";

// --- Helpers ---

/** Minimal valid TabularData for testing. */
function makeTabularData() {
  return {
    columns: [
      { name: "Entity", dataType: "STRING" as const, nullable: true },
      { name: "Account", dataType: "STRING" as const, nullable: true },
      { name: "DC", dataType: "STRING" as const, nullable: true },
      { name: "jan-26", dataType: "FLOAT" as const, nullable: true },
    ],
    rows: [
      {
        values: [
          { type: "string" as const, value: "E1" },
          { type: "string" as const, value: "A1" },
          { type: "string" as const, value: "D" },
          { type: "float" as const, value: 100.0 },
        ],
      },
    ],
    rowCount: 1,
    metadata: {
      sourceName: "Budget",
      sourceFormat: "EXCEL" as const,
      importedAt: null,
      transformedAt: null,
      exportedAt: null,
      encoding: "utf-8",
    },
  };
}

function makeMappingConfig() {
  return {
    entityColumn: "Entity",
    accountColumn: "Account",
    dcColumn: "DC",
    monthColumns: [{ sourceColumnName: "jan-26", periodNumber: 1, year: 2026 }],
  };
}

function makeTemplate() {
  return {
    packageName: "afas",
    templateName: "budget",
    columns: [
      {
        name: "Entity",
        dataType: "STRING" as const,
        nullable: false,
        sourceMapping: { type: "from_source" as const, sourceColumnName: "Entity" },
      },
    ],
  };
}

/** Create a mock File object. */
function makeFile(size = 1024): File {
  const buf = new ArrayBuffer(size);
  return new File([buf], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

/**
 * Configure all mocks to succeed by default.
 * Individual tests override specific mocks to inject failures.
 */
function setupAllSuccess() {
  const data = makeTabularData();
  const mapping = makeMappingConfig();
  const template = makeTemplate();

  vi.mocked(validateFileSize).mockImplementation(() => {});
  vi.mocked(parseExcelFile).mockReturnValue({ SheetNames: ["Budget"] } as any);
  vi.mocked(scanForHeaderRow).mockReturnValue({
    candidateRows: [0],
    rawPreview: [["Entity", "Account", "DC", "jan-26"]],
  });
  vi.mocked(extractBudgetData).mockReturnValue(data);
  vi.mocked(extractMappingConfig).mockReturnValue(mapping);
  vi.mocked(validateMappingConfig).mockReturnValue({ valid: true, errors: [] });
  vi.mocked(validateUserParams).mockReturnValue({ valid: true, errors: [] });
  vi.mocked(validateDCValues).mockReturnValue({ valid: true, errors: [] });
  vi.mocked(getTemplate).mockResolvedValue({ ok: true, data: template });
  vi.mocked(generateTransformSql).mockReturnValue("SELECT 1");
  vi.mocked(duckdb.initialize).mockResolvedValue(undefined);
  vi.mocked(duckdb.registerTable).mockResolvedValue(undefined);
  vi.mocked(duckdb.executeSql).mockResolvedValue(data);
}

// --- Import step definitions ---

/** Steps in importFile flow, in order. */
const IMPORT_STEPS: PipelineStep[] = [
  "memory_guard",
  "excel_parse",
  "extract_data",
  "extract_mapping",
];

/** Steps in runTransform flow, in order. */
const TRANSFORM_STEPS: PipelineStep[] = [
  "validate_mapping",
  "validate_params",
  "validate_dc",
  "fetch_template",
  "sql_generation",
  "duckdb_execute",
];

describe("Property 16: Pipeline Halt on Failure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupAllSuccess();
  });

  it("importFile: if step N fails, no step after N executes", async () => {
    // For each possible failure point in the import pipeline,
    // verify that steps after the failure are not executed.
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: IMPORT_STEPS.length - 1 }),
        fc.string({ minLength: 1, maxLength: 50 }),
        async (failIndex, errorMsg) => {
          vi.clearAllMocks();
          setupAllSuccess();

          const failStep = IMPORT_STEPS[failIndex];

          // Inject failure at the chosen step
          switch (failStep) {
            case "memory_guard":
              vi.mocked(validateFileSize).mockImplementation(() => {
                throw new Error(errorMsg);
              });
              break;
            case "excel_parse":
              vi.mocked(parseExcelFile).mockReturnValue(
                new ParseError(errorMsg),
              );
              break;
            case "extract_data":
              vi.mocked(extractBudgetData).mockReturnValue(
                new ParseError(errorMsg),
              );
              break;
            case "extract_mapping":
              vi.mocked(extractMappingConfig).mockReturnValue(
                new MappingError(errorMsg),
              );
              break;
          }

          const orch = new PipelineOrchestrator();
          const result = await orch.importFile(makeFile());

          // Pipeline should return an error
          expect(result.ok).toBe(false);
          if (!result.ok) {
            expect(result.error).toBeTruthy();
            expect(result.error.length).toBeGreaterThan(0);
          }

          // The trace should contain only steps up to and including the failed step
          const trace = orch.trace;
          const expectedSteps = IMPORT_STEPS.slice(0, failIndex + 1);
          expect(trace.executedSteps).toEqual(expectedSteps);
          expect(trace.failedStep).toBe(failStep);

          // No step after failIndex should have executed
          for (let i = failIndex + 1; i < IMPORT_STEPS.length; i++) {
            expect(trace.executedSteps).not.toContain(IMPORT_STEPS[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("runTransform: if step N fails, no step after N executes", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 0, max: TRANSFORM_STEPS.length - 1 }),
        fc.string({ minLength: 1, maxLength: 50 }),
        async (failIndex, errorMsg) => {
          vi.clearAllMocks();
          setupAllSuccess();

          const failStep = TRANSFORM_STEPS[failIndex];

          // Inject failure at the chosen step
          switch (failStep) {
            case "validate_mapping":
              vi.mocked(validateMappingConfig).mockReturnValue({
                valid: false,
                errors: [errorMsg],
              });
              break;
            case "validate_params":
              vi.mocked(validateUserParams).mockReturnValue({
                valid: false,
                errors: [errorMsg],
              });
              break;
            case "validate_dc":
              vi.mocked(validateDCValues).mockReturnValue({
                valid: false,
                errors: [errorMsg],
              });
              break;
            case "fetch_template":
              // Template not set — orchestrator checks this
              break;
            case "sql_generation":
              vi.mocked(generateTransformSql).mockImplementation(() => {
                throw new Error(errorMsg);
              });
              break;
            case "duckdb_execute":
              vi.mocked(duckdb.executeSql).mockRejectedValue(
                new Error(errorMsg),
              );
              break;
          }

          // Set up the orchestrator with pre-loaded state
          const orch = new PipelineOrchestrator();

          // Directly set internal state via importFile success
          const importResult = await orch.importFile(makeFile());
          expect(importResult.ok).toBe(true);

          orch.setParams("BC001", 2026);

          // Set template unless we're testing the fetch_template failure
          if (failStep !== "fetch_template") {
            await orch.selectTemplate("afas", "budget");
          }

          const result = await orch.runTransform();

          // Pipeline should return an error
          expect(result.ok).toBe(false);
          if (!result.ok) {
            expect(result.error).toBeTruthy();
            expect(result.error.length).toBeGreaterThan(0);
          }

          // The trace should contain only steps up to and including the failed step
          const trace = orch.trace;
          const expectedSteps = TRANSFORM_STEPS.slice(0, failIndex + 1);
          expect(trace.executedSteps).toEqual(expectedSteps);
          expect(trace.failedStep).toBe(failStep);

          // No step after failIndex should have executed
          for (let i = failIndex + 1; i < TRANSFORM_STEPS.length; i++) {
            expect(trace.executedSteps).not.toContain(TRANSFORM_STEPS[i]);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("successful pipeline executes all steps with no failure", async () => {
    const orch = new PipelineOrchestrator();

    const importResult = await orch.importFile(makeFile());
    expect(importResult.ok).toBe(true);
    expect(orch.trace.executedSteps).toEqual(IMPORT_STEPS);
    expect(orch.trace.failedStep).toBeNull();

    orch.setParams("BC001", 2026);
    await orch.selectTemplate("afas", "budget");

    const transformResult = await orch.runTransform();
    expect(transformResult.ok).toBe(true);
    expect(orch.trace.executedSteps).toEqual(TRANSFORM_STEPS);
    expect(orch.trace.failedStep).toBeNull();
  });
});
