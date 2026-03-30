"""Pipeline orchestrator for the excel2budget conversion module.

Coordinates Excel import, DuckDB transformation, template registry,
and format export. Handles null-account filtering, invalid DC detection,
and date stamping.

Requirements: 5.1, 5.2, 5.9, 5.10, 14.1, 10.1, 10.2, 19.1, 19.2
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import duckdb

from src.core.types import (
    CellValue,
    ColumnDef,
    DataMetadata,
    DataType,
    FileFormat,
    FloatVal,
    IntVal,
    MappingConfig,
    NullVal,
    OutputTemplate,
    Row,
    StringVal,
    TabularData,
    TableRef,
    TransformError,
    TransformResult,
    TransformSuccess,
    UserParams,
)
from src.core.validation import (
    validate_mapping_config,
    validate_user_params,
)
from src.engine.duckdb.engine import (
    execute_sql,
    initialize,
    register_table,
)
from src.modules.excel2budget.sql_generator import (
    SQLGenerationError,
    generate_transform_sql,
)


def _find_invalid_dc_values(
    data: TabularData,
    dc_column: str,
) -> List[Tuple[int, str]]:
    """Find rows with DC values other than 'D' or 'C'.

    Returns a list of (row_index, invalid_value) tuples.
    """
    dc_idx: Optional[int] = None
    for i, col in enumerate(data.columns):
        if col.name == dc_column:
            dc_idx = i
            break
    if dc_idx is None:
        return []

    invalid: List[Tuple[int, str]] = []
    for row_idx, row in enumerate(data.rows):
        cell = row.values[dc_idx]
        if isinstance(cell, NullVal):
            invalid.append((row_idx, "NULL"))
        elif isinstance(cell, StringVal):
            if cell.value not in ("D", "C"):
                invalid.append((row_idx, cell.value))
        else:
            invalid.append((row_idx, str(cell)))
    return invalid


def _filter_null_accounts(
    data: TabularData,
    account_column: str,
) -> TabularData:
    """Return a copy of data with rows where account is null removed."""
    acc_idx: Optional[int] = None
    for i, col in enumerate(data.columns):
        if col.name == account_column:
            acc_idx = i
            break
    if acc_idx is None:
        return data

    filtered_rows = [
        row for row in data.rows
        if not isinstance(row.values[acc_idx], NullVal)
    ]
    return TabularData(
        columns=list(data.columns),
        rows=filtered_rows,
        rowCount=len(filtered_rows),
        metadata=DataMetadata(
            sourceName=data.metadata.sourceName,
            sourceFormat=data.metadata.sourceFormat,
            importedAt=data.metadata.importedAt,
            encoding=data.metadata.encoding,
        ),
    )


def _retype_result(
    raw: TabularData,
    template: OutputTemplate,
) -> TabularData:
    """Re-type the DuckDB result columns to match the OutputTemplate schema."""
    new_columns = [
        ColumnDef(
            name=tc.name,
            dataType=tc.dataType,
            nullable=tc.nullable,
        )
        for tc in template.columns
    ]
    new_rows: List[Row] = []
    for row in raw.rows:
        new_vals: List[CellValue] = []
        for i, tc in enumerate(template.columns):
            cell = row.values[i]
            if isinstance(cell, NullVal):
                new_vals.append(cell)
            elif tc.dataType == DataType.INTEGER:
                new_vals.append(IntVal(int(float(str(_cell_value(cell))))))
            elif tc.dataType == DataType.FLOAT:
                val = _cell_value(cell)
                new_vals.append(FloatVal(float(val)) if val is not None else NullVal())
            else:
                new_vals.append(StringVal(str(_cell_value(cell))))
        new_rows.append(Row(new_vals))
    return TabularData(
        columns=new_columns,
        rows=new_rows,
        rowCount=len(new_rows),
        metadata=raw.metadata,
    )


def _cell_value(cell: CellValue):
    """Extract the raw Python value from a CellValue."""
    if isinstance(cell, NullVal):
        return None
    return cell.value  # type: ignore[union-attr]


def run_budget_transformation(
    source_data: TabularData,
    mapping_config: MappingConfig,
    template: OutputTemplate,
    user_params: UserParams,
    db: Optional[duckdb.DuckDBPyConnection] = None,
) -> TransformResult:
    """Execute the full budget transformation pipeline.

    1. Validate inputs
    2. Check for invalid DC values
    3. Filter null-account rows
    4. Register data in DuckDB
    5. Generate and execute transformation SQL
    6. Re-type result to match template schema
    7. Record date stamps

    Args:
        source_data: The budget TabularData to transform.
        mapping_config: Column mapping configuration.
        template: Target output template.
        user_params: User-specified parameters (budgetcode, year).
        db: Optional existing DuckDB connection (created if None).

    Returns:
        TransformSuccess with the transformed data, or TransformError.
    """
    # Validate inputs
    col_names = [c.name for c in source_data.columns]
    mc_result = validate_mapping_config(mapping_config, col_names)
    if not mc_result.valid:
        return TransformError(
            message="Invalid MappingConfig: " + "; ".join(mc_result.errors)
        )

    up_result = validate_user_params(user_params)
    if not up_result.valid:
        return TransformError(
            message="Invalid UserParams: " + "; ".join(up_result.errors)
        )

    # Check for invalid DC values (before filtering)
    invalid_dc = _find_invalid_dc_values(source_data, mapping_config.dcColumn)
    if invalid_dc:
        details = ", ".join(
            f"row {idx}: {val!r}" for idx, val in invalid_dc
        )
        return TransformError(
            message=f"Invalid DC values found: {details}"
        )

    # Filter null-account rows
    filtered = _filter_null_accounts(source_data, mapping_config.accountColumn)

    # Generate SQL
    try:
        sql = generate_transform_sql(mapping_config, template, user_params)
    except SQLGenerationError as e:
        return TransformError(message=f"SQL generation failed: {e}")

    # Execute transformation
    own_db = db is None
    if own_db:
        db = initialize()

    try:
        start_ms = time.monotonic_ns() // 1_000_000
        register_table(db, filtered, "budget")
        raw_result = execute_sql(db, sql)
        elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

        # Re-type to match template schema
        typed_result = _retype_result(raw_result, template)
        typed_result.metadata.transformedAt = datetime.now(timezone.utc)
        typed_result.metadata.importedAt = source_data.metadata.importedAt

        return TransformSuccess(data=typed_result, executionTimeMs=int(elapsed))

    except Exception as e:
        sql_state = ""
        if hasattr(e, "sqlstate"):
            sql_state = str(e.sqlstate)
        return TransformError(message=str(e), sqlState=sql_state)

    finally:
        if own_db and db is not None:
            db.close()
