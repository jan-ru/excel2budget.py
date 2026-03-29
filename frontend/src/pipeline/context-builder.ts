/**
 * ApplicationContext builder for the excel2budget frontend module.
 *
 * Builds an ApplicationContext from session data containing only metadata
 * and aggregates — no raw financial data is included. Computes control
 * totals for reconciliation.
 *
 * Port of `src/modules/excel2budget/context_builder.py`.
 *
 * Requirements: 5.2, 18.3
 */

import type { components } from "../types/api";

// --- Type aliases ---
type TabularData = components["schemas"]["TabularData"];
type MappingConfig = components["schemas"]["MappingConfig"];
type OutputTemplate = components["schemas"]["OutputTemplate"];
type UserParams = components["schemas"]["UserParams"];
type ApplicationContext = components["schemas"]["ApplicationContext"];
type ControlTotals = components["schemas"]["ControlTotals"];
type NamedTotal = components["schemas"]["NamedTotal"];
type BalanceCheck = components["schemas"]["BalanceCheck"];
type DataDescription = components["schemas"]["DataDescription"];
type ColumnDescription = components["schemas"]["ColumnDescription"];
type SystemDescriptor = components["schemas"]["SystemDescriptor"];
type ProcessStep = components["schemas"]["ProcessStep"];
type TransformDescriptor = components["schemas"]["TransformDescriptor"];
type CellValue = components["schemas"]["Row"]["values"][number];

// --- Session info passed to the builder ---
export interface SessionInfo {
  sourceFileName: string;
  packageName: string;
  templateName: string;
  userParams: UserParams;
  configurationDate?: string | null;
}

// --- Internal helpers ---

function findColumnIndex(data: TabularData, name: string): number {
  return data.columns.findIndex((c) => c.name === name);
}

function cellToFloat(cell: CellValue): number {
  switch (cell.type) {
    case "int":
    case "float":
      return cell.value;
    case "string": {
      const n = parseFloat(cell.value);
      return isNaN(n) ? 0.0 : n;
    }
    default:
      return 0.0;
  }
}

/**
 * Compute reconciliation control totals from source and transformed data.
 *
 * Input totals match the transformation output logic:
 * - DC="D" rows: add ROUND(value, 4) per month (preserves sign)
 * - DC="C" rows: add ROUND(ABS(value), 4) per month
 */
export function computeControlTotals(
  sourceData: TabularData,
  transformedData: TabularData,
  mappingConfig: MappingConfig,
): ControlTotals {
  const accIdx = findColumnIndex(sourceData, mappingConfig.accountColumn);
  const dcIdx = findColumnIndex(sourceData, mappingConfig.dcColumn);
  const monthIndices = mappingConfig.monthColumns.map((mc) =>
    findColumnIndex(sourceData, mc.sourceColumnName),
  );

  let inputRowCount = 0;
  let inputValueTotal = 0.0;

  for (const row of sourceData.rows) {
    if (accIdx >= 0 && row.values[accIdx].type === "null") continue;
    inputRowCount++;

    let dcVal = "";
    if (dcIdx >= 0 && row.values[dcIdx].type === "string") {
      dcVal = (row.values[dcIdx] as { type: "string"; value: string }).value;
    }

    for (const mi of monthIndices) {
      if (mi >= 0 && row.values[mi].type !== "null") {
        const raw = cellToFloat(row.values[mi]);
        if (dcVal === "C") {
          inputValueTotal += Math.round(Math.abs(raw) * 10000) / 10000;
        } else {
          inputValueTotal += Math.round(raw * 10000) / 10000;
        }
      }
    }
  }

  // Output totals
  const debetIdx = findColumnIndex(transformedData, "Debet");
  const creditIdx = findColumnIndex(transformedData, "Credit");
  let outputDebetTotal = 0.0;
  let outputCreditTotal = 0.0;

  for (const row of transformedData.rows) {
    if (debetIdx >= 0 && row.values[debetIdx].type !== "null") {
      outputDebetTotal += cellToFloat(row.values[debetIdx]);
    }
    if (creditIdx >= 0 && row.values[creditIdx].type !== "null") {
      outputCreditTotal += cellToFloat(row.values[creditIdx]);
    }
  }

  const balanceOk = Math.abs(inputValueTotal - (outputDebetTotal + outputCreditTotal)) < 0.01;

  return {
    inputRowCount,
    outputRowCount: transformedData.rowCount,
    inputTotals: [{ label: "Budget Values", value: inputValueTotal }],
    outputTotals: [
      { label: "Debet", value: outputDebetTotal },
      { label: "Credit", value: outputCreditTotal },
    ],
    balanceChecks: [
      {
        description: "Sum of input values = Sum of Debet + Sum of Credit",
        passed: balanceOk,
      },
    ],
  };
}

function buildSourceDescription(
  sourceData: TabularData,
  mappingConfig: MappingConfig,
): DataDescription {
  const monthColNames = new Set(
    mappingConfig.monthColumns.map((mc) => mc.sourceColumnName),
  );

  const columns: ColumnDescription[] = sourceData.columns.map((col) => {
    let source: string;
    if (col.name === mappingConfig.entityColumn) {
      source = "Mapping: Entity column";
    } else if (col.name === mappingConfig.accountColumn) {
      source = "Mapping: Account column";
    } else if (col.name === mappingConfig.dcColumn) {
      source = "Mapping: DC flag column";
    } else if (monthColNames.has(col.name)) {
      const mc = mappingConfig.monthColumns.find(
        (m) => m.sourceColumnName === col.name,
      )!;
      source = `Mapping: Month column (period ${mc.periodNumber})`;
    } else {
      source = "Unmapped";
    }

    return {
      name: col.name,
      dataType: col.dataType,
      description: `Source column: ${col.name}`,
      source,
    };
  });

  return {
    name: "Budget Excel File",
    columns,
    additionalNotes:
      `Entity: ${mappingConfig.entityColumn}, ` +
      `Account: ${mappingConfig.accountColumn}, ` +
      `DC: ${mappingConfig.dcColumn}, ` +
      `Month columns: ${mappingConfig.monthColumns.length}`,
  };
}

function buildTargetDescription(template: OutputTemplate): DataDescription {
  const columns: ColumnDescription[] = template.columns.map((col) => {
    let source: string;
    switch (col.sourceMapping.type) {
      case "from_source":
        source = `Source column: ${col.sourceMapping.sourceColumnName}`;
        break;
      case "from_user_param":
        source = `User parameter: ${col.sourceMapping.paramName}`;
        break;
      case "from_transform":
        source = `Transform: ${col.sourceMapping.expression}`;
        break;
      case "fixed_null":
        source = "Fixed: null";
        break;
      default:
        source = "Unknown";
    }

    return {
      name: col.name,
      dataType: col.dataType,
      description: `Target column: ${col.name}`,
      source,
    };
  });

  return {
    name: `${template.packageName} ${template.templateName} Import`,
    columns,
    additionalNotes: `Package: ${template.packageName}, Template: ${template.templateName}`,
  };
}

/**
 * Build an ApplicationContext from session data.
 *
 * Contains only metadata and aggregates — no raw financial data.
 * Suitable for sending to the backend documentation endpoint.
 */
export function buildApplicationContext(
  session: SessionInfo,
  sourceData: TabularData,
  transformedData: TabularData,
  mappingConfig: MappingConfig,
  template: OutputTemplate,
  sql: string,
): ApplicationContext {
  return {
    applicationName: "excel2budget",
    configurationName: `${session.packageName} ${session.templateName} ${session.userParams.year}`,
    configurationDate: session.configurationDate ?? null,
    sourceSystem: {
      name: "Excel",
      systemType: "Spreadsheet",
      description: `Budget file: ${session.sourceFileName}`,
    },
    targetSystem: {
      name: session.packageName,
      systemType: "Accounting Package",
      description: `${session.templateName} import`,
    },
    intermediarySystems: [
      { name: "IronCalc WASM", systemType: "Conversion Tool", description: "Spreadsheet preview" },
      { name: "DuckDB WASM", systemType: "Conversion Tool", description: "SQL transformation engine" },
    ],
    processSteps: [
      { stepNumber: 1, name: "Upload Excel File", description: "User uploads budget .xlsx file", actor: "User" },
      { stepNumber: 2, name: "Extract Mapping", description: "System reads column mapping from Excel", actor: "System" },
      { stepNumber: 3, name: "Set Parameters", description: "User specifies budgetcode and year", actor: "User" },
      { stepNumber: 4, name: "Run Transformation", description: "DuckDB executes unpivot + DC split", actor: "System" },
      { stepNumber: 5, name: "Review Output", description: "User reviews transformed data in IronCalc", actor: "User" },
      { stepNumber: 6, name: "Export", description: "User downloads result as CSV/Excel", actor: "User" },
    ],
    sourceDescription: buildSourceDescription(sourceData, mappingConfig),
    targetDescription: buildTargetDescription(template),
    transformDescription: {
      name: "Budget Unpivot + DC Split",
      description: "Transforms wide-format budget data into long-format accounting import",
      steps: [
        "Filter rows with null account values",
        "UNPIVOT month columns into (Period, Value) rows",
        "Extract period number from month column mapping",
        "Split Value into Debet/Credit based on DC flag",
        "Add fixed columns (Budgetcode, null placeholders)",
        "Reorder columns per output template",
      ],
      generatedQuery: sql,
    },
    controlTotals: computeControlTotals(sourceData, transformedData, mappingConfig),
    userInstructionSteps: [
      "Upload your budget Excel file containing the Budget sheet",
      "Verify the column mapping (Entity, Account, DC, month columns)",
      `Select the target accounting package: ${session.packageName}`,
      `Select the template: ${session.templateName}`,
      `Enter the budgetcode: ${session.userParams.budgetcode}`,
      `Enter the year: ${session.userParams.year}`,
      "Click 'Run Transformation' to execute the conversion",
      "Review the transformed data in the output preview",
      "Export the result as CSV or Excel for import into your accounting package",
    ],
  };
}
