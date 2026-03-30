/**
 * DuckDB-WASM engine wrapper for in-browser SQL execution.
 *
 * Wraps @duckdb/duckdb-wasm to provide table registration from TabularData,
 * SQL execution returning TabularData, and lifecycle management.
 *
 * Requirements: 8.3, 16.2
 */

import * as duckdb from "@duckdb/duckdb-wasm";
import duckdb_mvp_wasm from "@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url";
import duckdb_mvp_worker from "@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url";
import duckdb_eh_wasm from "@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url";
import duckdb_eh_worker from "@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url";
import * as arrow from "apache-arrow";
import type { components } from "../types/api";

// --- Type aliases from generated API types ---
type TabularData = components["schemas"]["TabularData"];
type ColumnDef = components["schemas"]["ColumnDef"];
type Row = components["schemas"]["Row"];
type DataType = components["schemas"]["DataType"];
type CellValue = Row["values"][number];

// --- Error types ---

export class DuckDBEngineError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DuckDBEngineError";
  }
}

export class TableNameError extends DuckDBEngineError {
  constructor(name: string) {
    super(
      `Invalid table name '${name}': must match [a-zA-Z_][a-zA-Z0-9_]*`,
    );
    this.name = "TableNameError";
  }
}

// --- Constants ---

const TABLE_NAME_RE = /^[a-zA-Z_][a-zA-Z0-9_]*$/;

/** DataType → DuckDB SQL type */
const DATATYPE_TO_SQL: Record<DataType, string> = {
  STRING: "VARCHAR",
  INTEGER: "BIGINT",
  FLOAT: "DOUBLE",
  BOOLEAN: "BOOLEAN",
  DATE: "DATE",
  DATETIME: "TIMESTAMP",
  NULL: "VARCHAR",
};

/** Arrow type ID → DataType reverse mapping */
function arrowTypeToDataType(arrowType: arrow.DataType): DataType {
  if (arrow.DataType.isUtf8(arrowType)) return "STRING";
  if (arrow.DataType.isInt(arrowType)) return "INTEGER";
  if (
    arrow.DataType.isFloat(arrowType) ||
    arrow.DataType.isDecimal(arrowType)
  )
    return "FLOAT";
  if (arrow.DataType.isBool(arrowType)) return "BOOLEAN";
  if (arrow.DataType.isDate(arrowType)) return "DATE";
  if (arrow.DataType.isTimestamp(arrowType)) return "DATETIME";
  return "STRING";
}

// --- Value conversion helpers ---

function cellToSql(cell: CellValue): unknown {
  if (cell.type === "null") return null;
  return cell.value;
}

function arrowValueToCell(
  value: unknown,
  dataType: DataType,
): CellValue {
  if (value === null || value === undefined) {
    return { type: "null" };
  }
  switch (dataType) {
    case "STRING":
    case "NULL":
      return { type: "string", value: String(value) };
    case "INTEGER":
      return { type: "int", value: Number(value) };
    case "FLOAT":
      return { type: "float", value: Number(value) };
    case "BOOLEAN":
      return { type: "bool", value: Boolean(value) };
    case "DATE":
    case "DATETIME":
      return { type: "date", value: String(value) };
    default:
      return { type: "string", value: String(value) };
  }
}

function validateTableName(name: string): void {
  if (!TABLE_NAME_RE.test(name)) {
    throw new TableNameError(name);
  }
}

// --- Engine state ---

interface EngineState {
  db: duckdb.AsyncDuckDB;
  conn: duckdb.AsyncDuckDBConnection;
}

let state: EngineState | null = null;

// --- Public API ---

/**
 * Initialize the DuckDB-WASM engine.
 *
 * Selects the appropriate WASM bundle for the current browser,
 * instantiates the database, and opens a connection.
 */
export async function initialize(): Promise<void> {
  if (state) return; // already initialized

  const DUCKDB_BUNDLES = await pickBundles();
  const bundle = await duckdb.selectBundle(DUCKDB_BUNDLES);

  const worker = new Worker(bundle.mainWorker!);
  const logger = new duckdb.ConsoleLogger();
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule);

  const conn = await db.connect();
  state = { db, conn };
}

/**
 * Register a TabularData instance as a named table.
 *
 * Creates the table with matching column types and inserts all rows.
 */
export async function registerTable(
  data: TabularData,
  tableName: string,
): Promise<void> {
  assertInitialized();
  validateTableName(tableName);

  const colDefs = data.columns
    .map((c) => `"${escapeIdent(c.name)}" ${DATATYPE_TO_SQL[c.dataType]}`)
    .join(", ");

  await state!.conn.query(`CREATE TABLE "${escapeIdent(tableName)}" (${colDefs})`);

  if (data.rows.length > 0) {
    const placeholders = data.columns.map(() => "?").join(", ");
    const insertSql = `INSERT INTO "${escapeIdent(tableName)}" VALUES (${placeholders})`;
    const stmt = await state!.conn.prepare(insertSql);

    for (const row of data.rows) {
      await stmt.query(...row.values.map(cellToSql));
    }
    await stmt.close();
  }
}

/**
 * Execute a SQL query and return the result as TabularData.
 *
 * Column types are inferred from the Arrow result schema.
 */
export async function executeSql(sql: string): Promise<TabularData> {
  assertInitialized();

  const result: arrow.Table = await state!.conn.query(sql);
  const schema = result.schema;

  const columns: ColumnDef[] = schema.fields.map((f) => ({
    name: f.name,
    dataType: arrowTypeToDataType(f.type),
    nullable: f.nullable,
  }));

  const rows: Row[] = [];
  for (let i = 0; i < result.numRows; i++) {
    const arrowRow = result.get(i);
    const values: CellValue[] = columns.map((col) => {
      const val = arrowRow?.[col.name];
      return arrowValueToCell(val, col.dataType);
    });
    rows.push({ values });
  }

  return {
    columns,
    rows,
    rowCount: result.numRows,
    metadata: {
      sourceName: "",
      sourceFormat: "EXCEL",
      importedAt: null,
      transformedAt: new Date().toISOString(),
      exportedAt: null,
      encoding: "utf-8",
    },
  };
}

/**
 * Close the DuckDB-WASM engine, releasing all resources.
 */
export async function close(): Promise<void> {
  if (!state) return;
  await state.conn.close();
  await state.db.terminate();
  state = null;
}

/**
 * Check whether the engine is currently initialized.
 */
export function isInitialized(): boolean {
  return state !== null;
}

// --- Internal helpers ---

function assertInitialized(): void {
  if (!state) {
    throw new DuckDBEngineError(
      "DuckDB engine not initialized. Call initialize() first.",
    );
  }
}

/** Escape a SQL identifier by doubling internal double-quotes. */
function escapeIdent(name: string): string {
  return name.replace(/"/g, '""');
}

/**
 * Build DuckDB bundle paths.
 *
 * Uses Vite's ?url imports so asset URLs are resolved correctly
 * in both dev and production builds.
 */
async function pickBundles(): Promise<duckdb.DuckDBBundles> {
  return {
    mvp: {
      mainModule: duckdb_mvp_wasm,
      mainWorker: duckdb_mvp_worker,
    },
    eh: {
      mainModule: duckdb_eh_wasm,
      mainWorker: duckdb_eh_worker,
    },
  };
}
