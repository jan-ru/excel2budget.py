/**
 * SQL generation for budget data transformation.
 *
 * Generates DuckDB-compatible SELECT-only SQL for the unpivot + DC split
 * transformation based on MappingConfig, OutputTemplate, and UserParams.
 * Uses quoted identifiers to prevent SQL injection.
 *
 * Requirements: 8.1, 8.2, 8.4
 */

import type { components } from "../types/api";

// --- Type aliases from generated API types ---
type MappingConfig = components["schemas"]["MappingConfig"];
type OutputTemplate = components["schemas"]["OutputTemplate"];
type UserParams = components["schemas"]["UserParams"];
type TemplateColumnDef = components["schemas"]["TemplateColumnDef"];

// --- Error type ---

export class SQLGenerationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SQLGenerationError";
  }
}

// --- NUL byte check ---
const NUL_RE = /\x00/;

// --- Public API ---

/**
 * Quote a column/table name for safe use in DuckDB SQL.
 *
 * Escapes embedded double-quotes by doubling them and wraps the
 * identifier in double-quotes. Rejects names containing NUL bytes or empty.
 */
export function quoteIdentifier(name: string): string {
  if (!name) {
    throw new SQLGenerationError("Identifier must be non-empty");
  }
  if (NUL_RE.test(name)) {
    throw new SQLGenerationError(`Identifier contains NUL byte: ${JSON.stringify(name)}`);
  }
  const escaped = name.replace(/"/g, '""');
  return `"${escaped}"`;
}

/**
 * Escape a string for use as a SQL string literal.
 * Doubles single quotes. Rejects null bytes.
 */
export function escapeStringLiteral(value: string): string {
  if (value.includes("\x00")) {
    throw new SQLGenerationError(`String literal contains null byte: ${JSON.stringify(value)}`);
  }
  return value.replace(/'/g, "''");
}


/**
 * Generate a DuckDB SELECT query that transforms budget data.
 *
 * The generated SQL:
 * - Is SELECT-only (no DDL/DML)
 * - References only the "budget" table
 * - Uses UNPIVOT for month columns, CASE for period extraction,
 *   DC-based Debet/Credit split
 * - Uses quoted identifiers to prevent SQL injection
 */
export function generateTransformSql(
  mappingConfig: MappingConfig,
  template: OutputTemplate,
  userParams: UserParams,
): string {
  if (!mappingConfig.monthColumns || mappingConfig.monthColumns.length === 0) {
    throw new SQLGenerationError("MappingConfig has no month columns");
  }

  // Build quoted month column list for UNPIVOT
  const monthCols = mappingConfig.monthColumns
    .map((mc) => quoteIdentifier(mc.sourceColumnName))
    .join(", ");

  const entityCol = quoteIdentifier(mappingConfig.entityColumn);
  const accountCol = quoteIdentifier(mappingConfig.accountColumn);
  const dcCol = quoteIdentifier(mappingConfig.dcColumn);

  // Build CASE branches mapping unpivoted column name -> period number
  const caseBranches = mappingConfig.monthColumns
    .map(
      (mc) =>
        `            WHEN '${escapeStringLiteral(mc.sourceColumnName)}' THEN ${mc.periodNumber}`,
    )
    .join("\n");

  const yearVal = Math.trunc(userParams.year);

  // Build the final SELECT column list from the template
  const selectColumns = buildSelectColumns(template, userParams);

  return `WITH unpivoted AS (
    SELECT
        ${entityCol} AS "Entity",
        ${accountCol} AS "Account",
        ${dcCol} AS "DC",
        "Period_Col",
        "Value"
    FROM "budget"
    UNPIVOT ("Value" FOR "Period_Col" IN (${monthCols}))
    WHERE ${accountCol} IS NOT NULL
),
with_periods AS (
    SELECT
        "Entity",
        "Account",
        "DC",
        "Value",
        ${yearVal} AS "Jaar",
        CASE "Period_Col"
${caseBranches}
        END AS "Periode"
    FROM unpivoted
)
SELECT
    ${selectColumns}
FROM with_periods
ORDER BY "Entity", "Account", "Periode"`;
}

// --- Internal helpers ---

function buildSelectColumns(
  template: OutputTemplate,
  userParams: UserParams,
): string {
  const parts: string[] = [];

  for (const colDef of template.columns) {
    const mapping = colDef.sourceMapping;
    const alias = quoteIdentifier(colDef.name);

    switch (mapping.type) {
      case "from_source": {
        const src = quoteIdentifier(mapping.sourceColumnName);
        parts.push(`CAST(${src} AS VARCHAR) AS ${alias}`);
        break;
      }
      case "from_user_param": {
        if (mapping.paramName === "budgetcode") {
          const lit = escapeStringLiteral(userParams.budgetcode);
          parts.push(`'${lit}' AS ${alias}`);
        } else if (mapping.paramName === "year") {
          parts.push(`${Math.trunc(userParams.year)} AS ${alias}`);
        } else {
          throw new SQLGenerationError(`Unknown user param: '${mapping.paramName}'`);
        }
        break;
      }
      case "from_transform": {
        const expr = mapping.expression;
        if (expr === "period_number") {
          parts.push(`"Periode" AS ${alias}`);
        } else if (expr.includes("DC") && expr.includes("ABS")) {
          // Credit: DC='C' -> ROUND(ABS(Value), 4)
          parts.push(
            `CASE WHEN "DC" = 'C' THEN ROUND(ABS(CAST("Value" AS DOUBLE)), 4) ELSE NULL END AS ${alias}`,
          );
        } else if (expr.includes("DC")) {
          // Debet: DC='D' -> ROUND(Value, 4)
          parts.push(
            `CASE WHEN "DC" = 'D' THEN ROUND(CAST("Value" AS DOUBLE), 4) ELSE NULL END AS ${alias}`,
          );
        } else {
          // Generic transform expression — use as-is (trusted template)
          parts.push(`${expr} AS ${alias}`);
        }
        break;
      }
      case "fixed_null": {
        parts.push(`NULL AS ${alias}`);
        break;
      }
      default: {
        throw new SQLGenerationError(
          `Unknown source mapping type: ${(mapping as { type: string }).type}`,
        );
      }
    }
  }

  return parts.join(",\n    ");
}
