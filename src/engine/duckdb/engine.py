"""DuckDB engine wrapper for the Data Conversion Tool pipeline.

Provides table registration, SQL execution, and table management
using DuckDB as the in-process analytical SQL engine.

Requirements: 7.1, 7.2, 7.3, 7.4
"""

from __future__ import annotations

import re
from typing import List

import duckdb

from src.core.types import (
    BoolVal,
    CellValue,
    ColumnDef,
    DataMetadata,
    DataType,
    DateVal,
    FloatVal,
    IntVal,
    NullVal,
    Row,
    StringVal,
    TabularData,
)

# Valid table name pattern (Req 7.4)
_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# DataType → DuckDB SQL type mapping
_DATATYPE_TO_SQL: dict[DataType, str] = {
    DataType.STRING: "VARCHAR",
    DataType.INTEGER: "BIGINT",
    DataType.FLOAT: "DOUBLE",
    DataType.BOOLEAN: "BOOLEAN",
    DataType.DATE: "DATE",
    DataType.DATETIME: "TIMESTAMP",
    DataType.NULL: "VARCHAR",
}

# DuckDB type name → DataType reverse mapping
_DUCKDB_TYPE_MAP: dict[str, DataType] = {
    "VARCHAR": DataType.STRING,
    "BIGINT": DataType.INTEGER,
    "INTEGER": DataType.INTEGER,
    "SMALLINT": DataType.INTEGER,
    "TINYINT": DataType.INTEGER,
    "HUGEINT": DataType.INTEGER,
    "DOUBLE": DataType.FLOAT,
    "FLOAT": DataType.FLOAT,
    "DECIMAL": DataType.FLOAT,
    "BOOLEAN": DataType.BOOLEAN,
    "DATE": DataType.DATE,
    "TIMESTAMP": DataType.DATETIME,
    "TIMESTAMP WITH TIME ZONE": DataType.DATETIME,
}


class TableNameError(Exception):
    """Raised when a table name does not match the allowed pattern."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_table_name(name: str) -> None:
    if not _TABLE_NAME_RE.match(name):
        raise TableNameError(
            f"Invalid table name '{name}': "
            "must match [a-zA-Z_][a-zA-Z0-9_]*"
        )


def _map_datatype(dt: DataType) -> str:
    """Return the DuckDB SQL type string for a DataType enum value."""
    return _DATATYPE_TO_SQL[dt]


def _cell_to_python(cell: CellValue):
    """Convert a CellValue variant to a plain Python value."""
    if isinstance(cell, StringVal):
        return cell.value
    if isinstance(cell, IntVal):
        return cell.value
    if isinstance(cell, FloatVal):
        return cell.value
    if isinstance(cell, BoolVal):
        return cell.value
    if isinstance(cell, DateVal):
        return cell.value
    if isinstance(cell, NullVal):
        return None
    raise TypeError(f"Unknown CellValue type: {type(cell)}")


def _python_to_cell(value, data_type: DataType) -> CellValue:
    """Convert a plain Python value from DuckDB back to a CellValue."""
    if value is None:
        return NullVal()
    if data_type in (DataType.STRING, DataType.NULL):
        return StringVal(str(value))
    if data_type == DataType.INTEGER:
        return IntVal(int(value))
    if data_type == DataType.FLOAT:
        return FloatVal(float(value))
    if data_type == DataType.BOOLEAN:
        return BoolVal(bool(value))
    if data_type in (DataType.DATE, DataType.DATETIME):
        return DateVal(str(value))
    return StringVal(str(value))


def _duckdb_type_to_datatype(duckdb_type: str) -> DataType:
    """Map a DuckDB type name string to our DataType enum."""
    upper = str(duckdb_type).upper()
    for key, dt in _DUCKDB_TYPE_MAP.items():
        if key in upper:
            return dt
    return DataType.STRING


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def initialize() -> duckdb.DuckDBPyConnection:
    """Create and return a new in-memory DuckDB connection."""
    return duckdb.connect(":memory:")


def register_table(
    db: duckdb.DuckDBPyConnection,
    data: TabularData,
    table_name: str,
) -> None:
    """Register a TabularData instance as a table in DuckDB.

    Creates a table with a schema matching the TabularData column
    definitions and inserts all rows.

    Raises:
        TableNameError: If *table_name* does not match
            ``[a-zA-Z_][a-zA-Z0-9_]*``.
    """
    _validate_table_name(table_name)

    col_defs = ", ".join(
        f'"{col.name}" {_map_datatype(col.dataType)}'
        for col in data.columns
    )
    db.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

    if data.rows:
        placeholders = ", ".join("?" for _ in data.columns)
        sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'
        for row in data.rows:
            db.execute(sql, [_cell_to_python(v) for v in row.values])


def execute_sql(
    db: duckdb.DuckDBPyConnection,
    sql: str,
) -> TabularData:
    """Execute a SQL query and return the result as TabularData.

    Column types are inferred from the DuckDB result description.
    """
    result = db.execute(sql)
    description = result.description or []
    rows_raw = result.fetchall()

    columns: List[ColumnDef] = [
        ColumnDef(name=d[0], dataType=_duckdb_type_to_datatype(d[1]))
        for d in description
    ]
    rows: List[Row] = [
        Row(values=[
            _python_to_cell(val, columns[i].dataType)
            for i, val in enumerate(raw)
        ])
        for raw in rows_raw
    ]
    return TabularData(
        columns=columns, rows=rows,
        rowCount=len(rows), metadata=DataMetadata(),
    )


def execute_sql_typed(
    db: duckdb.DuckDBPyConnection,
    sql: str,
    schema: List[ColumnDef],
) -> TabularData:
    """Execute a SQL query and map results using a known schema.

    Unlike *execute_sql*, this preserves the original DataType information
    so that round-trip fidelity can be verified.
    """
    result = db.execute(sql)
    rows_raw = result.fetchall()

    rows: List[Row] = [
        Row(values=[
            _python_to_cell(val, schema[i].dataType)
            for i, val in enumerate(raw)
        ])
        for raw in rows_raw
    ]
    return TabularData(
        columns=list(schema), rows=rows,
        rowCount=len(rows), metadata=DataMetadata(),
    )


def drop_table(db: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Drop a table from DuckDB.

    Raises:
        TableNameError: If *table_name* is invalid.
    """
    _validate_table_name(table_name)
    db.execute(f'DROP TABLE IF EXISTS "{table_name}"')


def list_tables(db: duckdb.DuckDBPyConnection) -> List[str]:
    """Return a list of user table names currently in DuckDB."""
    result = db.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    )
    return [row[0] for row in result.fetchall()]
