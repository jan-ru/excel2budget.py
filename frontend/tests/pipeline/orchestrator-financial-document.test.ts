/**
 * Tests for PipelineOrchestrator FinancialDocument production.
 *
 * Validates: Requirements 3.4, 3.5, 7.2
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { FinancialDocumentSchema } from "../../src/types/domain";

// --- Mock dependencies ---

vi.mock("../../src/guards/memory-guard", () => ({
  validateFileSize: vi.fn(),
}));

vi.mock("../../src/import/excel-importer", async () => {
  const actual = await vi.importActual<typeof import("../../src/import/excel-importer")>(
    "../../src/import/excel-importer",
  );
  return {
    ...actual,
    parseExcelFile: vi.fn(),
    extractBudgetData: vi.fn(),
    extractMappingConfig: vi.fn(),
    tabularBudgetToFinancialDocument: vi.fn(),
    scanForHeaderRow: vi.fn(),
    getSheetNames: vi.fn((wb: any) => wb?.SheetNames ?? []),
    hasSheet: vi.fn((wb: any, name: string) => (wb?.SheetNames ?? []).includes(name)),
  };
});

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
  tabularBudgetToFinancialDocument,
  scanForHeaderRow,
} from "../../src/import/excel-importer";

// --- Helpers ---

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

function makeFinancialDocument() {
  return {
    lines: [
      {
        account: "A1",
        entity: "E1",
        period: "2026-01",
        amount: "100.0000",
        line_type: "budget" as const,
        currency: "EUR",
        memo: null,
      },
    ],
    accounts: [
      {
        code: "A1",
        description: "A1",
        account_type: "expense" as const,
        normal_balance: "D" as const,
        parent_code: null,
      },
    ],
    entities: [
      {
        code: "E1",
        description: "E1",
        is_elimination: false,
      },
    ],
    meta: { source: "Budget" },
  };
}

function makeFile(size = 1024): File {
  const buf = new ArrayBuffer(size);
  return new File([buf], "test.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

function setupAllSuccess() {
  const data = makeTabularData();
  const mapping = makeMappingConfig();
  const fdoc = makeFinancialDocument();

  vi.mocked(validateFileSize).mockImplementation(() => {});
  vi.mocked(parseExcelFile).mockReturnValue({ SheetNames: ["Budget"] } as any);
  vi.mocked(scanForHeaderRow).mockReturnValue({
    candidateRows: [0],
    rawPreview: [["Entity", "Account", "DC", "jan-26"]],
  });
  vi.mocked(extractBudgetData).mockReturnValue(data);
  vi.mocked(extractMappingConfig).mockReturnValue(mapping);
  vi.mocked(tabularBudgetToFinancialDocument).mockReturnValue(
    FinancialDocumentSchema.parse(fdoc),
  );
}

// --- Tests ---

describe("PipelineOrchestrator FinancialDocument integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupAllSuccess();
  });

  it("produces a FinancialDocument after successful import", async () => {
    const orch = new PipelineOrchestrator();
    const result = await orch.importFile(makeFile());

    expect(result).toHaveProperty("ok", true);
    expect(orch.financialDocument).not.toBeNull();

    const parsed = FinancialDocumentSchema.safeParse(orch.financialDocument);
    expect(parsed.success).toBe(true);
  });

  it("financialDocument is null before import", () => {
    const orch = new PipelineOrchestrator();
    expect(orch.financialDocument).toBeNull();
  });

  it("financialDocument is cleared on reset", async () => {
    const orch = new PipelineOrchestrator();
    await orch.importFile(makeFile());
    expect(orch.financialDocument).not.toBeNull();

    orch.reset();
    expect(orch.financialDocument).toBeNull();
  });

  it("financialDocument contains expected lines", async () => {
    const orch = new PipelineOrchestrator();
    await orch.importFile(makeFile());

    const doc = orch.financialDocument;
    expect(doc).not.toBeNull();
    expect(doc!.lines).toHaveLength(1);
    expect(doc!.lines[0].account).toBe("A1");
    expect(doc!.lines[0].line_type).toBe("budget");
  });

  it("financialDocument is null when tabularBudgetToFinancialDocument throws", async () => {
    vi.mocked(tabularBudgetToFinancialDocument).mockImplementation(() => {
      throw new Error("conversion failed");
    });

    const orch = new PipelineOrchestrator();
    const result = await orch.importFile(makeFile());

    // Import still succeeds (TabularData path works)
    expect(result).toHaveProperty("ok", true);
    // But FinancialDocument is null
    expect(orch.financialDocument).toBeNull();
  });

  it("sourceData (TabularData) is still available alongside financialDocument", async () => {
    const orch = new PipelineOrchestrator();
    await orch.importFile(makeFile());

    expect(orch.sourceData).not.toBeNull();
    expect(orch.financialDocument).not.toBeNull();
  });
});
