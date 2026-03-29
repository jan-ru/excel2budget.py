/**
 * Property 8: SQL Generation Safety
 *
 * For any valid MappingConfig, OutputTemplate, and UserParams, the generated
 * SQL starts with WITH/SELECT (no DDL/DML), uses quoted identifiers, and
 * handles special characters in column names.
 *
 * Validates: Requirements 8.1, 8.2, 8.4
 */

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  generateTransformSql,
  quoteIdentifier,
  escapeStringLiteral,
  SQLGenerationError,
} from "../../src/transform/sql-generator";
import type { components } from "../../src/types/api";

type MappingConfig = components["schemas"]["MappingConfig"];
type MonthColumnDef = components["schemas"]["MonthColumnDef"];
type OutputTemplate = components["schemas"]["OutputTemplate"];
type TemplateColumnDef = components["schemas"]["TemplateColumnDef"];
type UserParams = components["schemas"]["UserParams"];

// --- Arbitraries ---

/** Safe column name: non-empty, no NUL bytes. */
const arbSafeColName = fc
  .stringOf(
    fc.char().filter((c) => c !== "\x00" && c.length > 0),
    { minLength: 1, maxLength: 20 },
  )
  .filter((s) => s.length > 0);

/** Column name with special characters (quotes, spaces, hyphens). */
const arbSpecialColName = fc.oneof(
  arbSafeColName,
  arbSafeColName.map((s) => `${s} col`),
  arbSafeColName.map((s) => `${s}-data`),
  arbSafeColName.map((s) => `"${s}"`),
  arbSafeColName.map((s) => `col'${s}`),
);

/** Generate a valid MappingConfig with 1–12 month columns. */
function arbMappingConfig(): fc.Arbitrary<MappingConfig> {
  return fc
    .integer({ min: 1, max: 12 })
    .chain((numMonths) => {
      const monthCols: fc.Arbitrary<MonthColumnDef[]> = fc.tuple(
        ...Array.from({ length: numMonths }, (_, i) =>
          arbSafeColName.map((name) => ({
            sourceColumnName: `month_${i}_${name}`,
            periodNumber: i + 1,
            year: 2026,
          })),
        ),
      );
      return fc.tuple(arbSafeColName, arbSafeColName, arbSafeColName, monthCols);
    })
    .map(([entity, account, dc, months]) => ({
      entityColumn: `ent_${entity}`,
      accountColumn: `acc_${account}`,
      dcColumn: `dc_${dc}`,
      monthColumns: months,
    }));
}

/** Generate a minimal valid OutputTemplate with all 4 mapping types. */
function arbOutputTemplate(): fc.Arbitrary<OutputTemplate> {
  const fromSource: TemplateColumnDef = {
    name: "Entity",
    dataType: "STRING",
    nullable: false,
    sourceMapping: { type: "from_source", sourceColumnName: "Entity" },
  };
  const fromUserBudgetcode: TemplateColumnDef = {
    name: "Budgetcode",
    dataType: "STRING",
    nullable: false,
    sourceMapping: { type: "from_user_param", paramName: "budgetcode" },
  };
  const fromUserYear: TemplateColumnDef = {
    name: "Year",
    dataType: "INTEGER",
    nullable: false,
    sourceMapping: { type: "from_user_param", paramName: "year" },
  };
  const fromTransformPeriod: TemplateColumnDef = {
    name: "Period",
    dataType: "INTEGER",
    nullable: false,
    sourceMapping: { type: "from_transform", expression: "period_number" },
  };
  const fromTransformDebet: TemplateColumnDef = {
    name: "Debet",
    dataType: "FLOAT",
    nullable: true,
    sourceMapping: { type: "from_transform", expression: "DC_debet" },
  };
  const fromTransformCredit: TemplateColumnDef = {
    name: "Credit",
    dataType: "FLOAT",
    nullable: true,
    sourceMapping: { type: "from_transform", expression: "DC_ABS_credit" },
  };
  const fixedNull: TemplateColumnDef = {
    name: "Reserved",
    dataType: "STRING",
    nullable: true,
    sourceMapping: { type: "fixed_null" },
  };

  return fc.constant({
    packageName: "test",
    templateName: "budget",
    columns: [
      fromSource,
      fromUserBudgetcode,
      fromUserYear,
      fromTransformPeriod,
      fromTransformDebet,
      fromTransformCredit,
      fixedNull,
    ],
  });
}

/** Generate valid UserParams. */
function arbUserParams(): fc.Arbitrary<UserParams> {
  return fc.record({
    budgetcode: fc
      .stringOf(fc.char().filter((c) => c !== "\x00" && c.length > 0), {
        minLength: 1,
        maxLength: 20,
      })
      .filter((s) => s.length > 0),
    year: fc.integer({ min: 2000, max: 2099 }),
  });
}

// --- DDL/DML keywords that must NOT appear at the start ---
const DDL_DML_KEYWORDS = [
  "CREATE",
  "DROP",
  "ALTER",
  "INSERT",
  "UPDATE",
  "DELETE",
  "TRUNCATE",
  "MERGE",
];

// ---------------------------------------------------------------------------
// Property 8: SQL Generation Safety
// ---------------------------------------------------------------------------

describe("Property 8: SQL Generation Safety", () => {
  it("generated SQL starts with WITH or SELECT (no DDL/DML)", () => {
    fc.assert(
      fc.property(
        arbMappingConfig(),
        arbOutputTemplate(),
        arbUserParams(),
        (mapping, template, params) => {
          const sql = generateTransformSql(mapping, template, params);
          const trimmed = sql.trimStart().toUpperCase();

          expect(trimmed.startsWith("WITH") || trimmed.startsWith("SELECT")).toBe(true);

          for (const kw of DDL_DML_KEYWORDS) {
            expect(trimmed.startsWith(kw)).toBe(false);
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("all user-supplied column names appear as quoted identifiers", () => {
    fc.assert(
      fc.property(
        arbMappingConfig(),
        arbOutputTemplate(),
        arbUserParams(),
        (mapping, template, params) => {
          const sql = generateTransformSql(mapping, template, params);

          // Entity, Account, DC columns should be quoted
          expect(sql).toContain(quoteIdentifier(mapping.entityColumn));
          expect(sql).toContain(quoteIdentifier(mapping.accountColumn));
          expect(sql).toContain(quoteIdentifier(mapping.dcColumn));

          // Month columns should be quoted in the UNPIVOT clause
          for (const mc of mapping.monthColumns) {
            expect(sql).toContain(quoteIdentifier(mc.sourceColumnName));
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("handles special characters in column names (quotes, spaces, hyphens)", () => {
    fc.assert(
      fc.property(arbSpecialColName, arbSpecialColName, (col1, col2) => {
        // Ensure distinct names
        if (col1 === col2) return;

        const mapping: MappingConfig = {
          entityColumn: col1,
          accountColumn: col2,
          dcColumn: "DC",
          monthColumns: [{ sourceColumnName: "jan-26", periodNumber: 1, year: 2026 }],
        };

        const template: OutputTemplate = {
          packageName: "test",
          templateName: "budget",
          columns: [
            {
              name: col1,
              dataType: "STRING",
              nullable: false,
              sourceMapping: { type: "from_source", sourceColumnName: "Entity" },
            },
          ],
        };

        const params: UserParams = { budgetcode: "ABC", year: 2026 };
        const sql = generateTransformSql(mapping, template, params);

        // Should not throw and should produce valid SQL
        expect(sql).toBeTruthy();
        expect(sql.trimStart().toUpperCase().startsWith("WITH")).toBe(true);
      }),
      { numRuns: 100 },
    );
  });

  it("budgetcode with single quotes is properly escaped in SQL", () => {
    fc.assert(
      fc.property(
        fc
          .stringOf(fc.char().filter((c) => c !== "\x00" && c.length > 0), {
            minLength: 1,
            maxLength: 20,
          })
          .filter((s) => s.length > 0),
        (budgetcode) => {
          const mapping: MappingConfig = {
            entityColumn: "Entity",
            accountColumn: "Account",
            dcColumn: "DC",
            monthColumns: [{ sourceColumnName: "jan-26", periodNumber: 1, year: 2026 }],
          };

          const template: OutputTemplate = {
            packageName: "test",
            templateName: "budget",
            columns: [
              {
                name: "Code",
                dataType: "STRING",
                nullable: false,
                sourceMapping: { type: "from_user_param", paramName: "budgetcode" },
              },
            ],
          };

          const sql = generateTransformSql(mapping, template, { budgetcode, year: 2026 });

          // The budgetcode should appear escaped (single quotes doubled)
          const escaped = escapeStringLiteral(budgetcode);
          expect(sql).toContain(`'${escaped}'`);

          // No unescaped single quotes from the budgetcode should break the SQL
          // (the escaped version should be present, not the raw version if it has quotes)
          if (budgetcode.includes("'")) {
            expect(sql).toContain(budgetcode.replace(/'/g, "''"));
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("throws SQLGenerationError for empty month columns", () => {
    const mapping: MappingConfig = {
      entityColumn: "Entity",
      accountColumn: "Account",
      dcColumn: "DC",
      monthColumns: [],
    };
    const template: OutputTemplate = {
      packageName: "test",
      templateName: "budget",
      columns: [],
    };
    const params: UserParams = { budgetcode: "ABC", year: 2026 };

    expect(() => generateTransformSql(mapping, template, params)).toThrow(SQLGenerationError);
  });

  it("throws SQLGenerationError for identifiers with NUL bytes", () => {
    expect(() => quoteIdentifier("col\x00name")).toThrow(SQLGenerationError);
    expect(() => quoteIdentifier("")).toThrow(SQLGenerationError);
    expect(() => escapeStringLiteral("val\x00ue")).toThrow(SQLGenerationError);
  });

  it("handles all four source mapping types correctly", () => {
    const mapping: MappingConfig = {
      entityColumn: "Entity",
      accountColumn: "Account",
      dcColumn: "DC",
      monthColumns: [{ sourceColumnName: "jan-26", periodNumber: 1, year: 2026 }],
    };

    const template: OutputTemplate = {
      packageName: "test",
      templateName: "budget",
      columns: [
        {
          name: "Ent",
          dataType: "STRING",
          nullable: false,
          sourceMapping: { type: "from_source", sourceColumnName: "Entity" },
        },
        {
          name: "Code",
          dataType: "STRING",
          nullable: false,
          sourceMapping: { type: "from_user_param", paramName: "budgetcode" },
        },
        {
          name: "Yr",
          dataType: "INTEGER",
          nullable: false,
          sourceMapping: { type: "from_user_param", paramName: "year" },
        },
        {
          name: "Period",
          dataType: "INTEGER",
          nullable: false,
          sourceMapping: { type: "from_transform", expression: "period_number" },
        },
        {
          name: "Debet",
          dataType: "FLOAT",
          nullable: true,
          sourceMapping: { type: "from_transform", expression: "DC_debet" },
        },
        {
          name: "Credit",
          dataType: "FLOAT",
          nullable: true,
          sourceMapping: { type: "from_transform", expression: "DC_ABS_credit" },
        },
        {
          name: "Empty",
          dataType: "STRING",
          nullable: true,
          sourceMapping: { type: "fixed_null" },
        },
      ],
    };

    const sql = generateTransformSql(mapping, template, { budgetcode: "TEST", year: 2026 });

    // from_source
    expect(sql).toContain('CAST("Entity" AS VARCHAR) AS "Ent"');
    // from_user_param budgetcode
    expect(sql).toContain("'TEST' AS \"Code\"");
    // from_user_param year
    expect(sql).toContain('2026 AS "Yr"');
    // from_transform period_number
    expect(sql).toContain('"Periode" AS "Period"');
    // from_transform DC debet
    expect(sql).toContain('WHEN "DC" = \'D\'');
    // from_transform DC credit (ABS)
    expect(sql).toContain('WHEN "DC" = \'C\'');
    expect(sql).toContain("ABS");
    // fixed_null
    expect(sql).toContain('NULL AS "Empty"');
  });
});
