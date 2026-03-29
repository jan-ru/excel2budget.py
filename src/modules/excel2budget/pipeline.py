"""Pipeline orchestrator for the excel2budget conversion module.

Wires together Excel importer, DuckDB engine, template registry,
and format exporter to perform the full budget conversion.

Requirements: 5.1, 5.2, 5.9, 5.10, 14.1, 10.1, 10.2, 19.1, 19.2
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

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


def _find_column_index(columns: List[ColumnDef], name: str) -> int:
    """Return the index of a column by name, or -1 if not found."""
    for i, col in enumerate(columns):
        if col.name == name:
            return i
    return -1


def _cell_to_str(cell: CellValue) -> str | None:
    """Extract a string value from a CellValue, or None for NullVal."""
    if isinstance(cell, NullVal):
        return None
    if isinstance(cell, StringVal):
        return cell.value
    if isinstance(cell, IntVal):
        return str(cell.value)
    if isinstance(cell, FloatVal):
        return str(cell.value)
    return str(cell)


def _validate_dc_values(
    data: TabularData,
    dc_column: str,
) -> List[Tuple[int, str]]:
    """Check for invalid DC values. Returns list of (row_index, value) pairs."""
    dc_idx = _find_column_index(data.columns, dc_column)
    if dc_idx < 0:
        return []

    invalid: List[Tuple[int, str]] = []
    for i, row in enumerate(data.rows):
        val = _cell_to_str(row.values[dc_idx])
        if val is not None and val not in ("D", "C"):
            invalid.append((i, val))
    return invalid


def _filter_null_accounts(
    data: TabularData,
    account_column: str,
) -> TabularData:
    """Return a new TabularData with rows having null account values removed."""
    acc_idx = _find_column_index(data.columns, account_column)
    if acc_idx < 0:
        return data

    filtered_rows = [
        row for row in data.rows
        if not isinstance(row.values[acc_idx], NullVal)
    ]
    return TabularData(
        columns=list(data.columns),
        rows=filtered_rows,
        rowCount=len(filtered_rows),
        metadata=data.metadata,
    )


def run_budget_transformation(
    budget_data: TabularData,
    mapping_config: MappingConfig,
    template: OutputTemplate,
    user_params: UserParams,
) -> TransformResult:
    """Execute the full budget transformation pipeline.

    Steps:
    1. Validate inputs (mapping config, user params)
    2. Filter null-account rows
    3. Detect invalid DC values
    4. Register data in DuckDB
    5. Generate and execute transformation SQL
    6. Return transformed data with metadata

    The source budget table in DuckDB is not modified (Req 10.1).
    """
    # Validate user params
    params_result = validate_user_params(user_params)
    if not params_result.valid:
        return TransformError(
            message=f"Invalid user params: {'; '.join(params_result.errors)}"
        )

    # Validate mapping config against source columns
    col_names = [col.name for col in budget_data.columns]
    mapping_result = validate_mapping_config(mapping_config, col_names)
    if not mapping_result.valid:
        return TransformError(
            message=f"Invalid mapping config: {'; '.join(mapping_result.errors)}"
        )

    # Filter null-account rows before checking DC values
    filtered_data = _filter_null_accounts(budget_data, mapping_config.accountColumn)

    # Detect invalid DC values in filtered data
    invalid_dc = _validate_dc_values(filtered_data, mapping_config.dcColumn)
    if invalid_dc:
        details = ", ".join(
            f"row {idx}: '{val}'" for idx, val in invalid_dc
        )
        return TransformError(
            message=f"Invalid DC values found: {details}"
        )

    # Generate SQL
    try:
        sql = generate_transform_sql(mapping_config, template, user_params)
    except SQLGenerationError as exc:
        return TransformError(message=f"SQL generation failed: {exc}")

    # Execute in DuckDB
    db: duckdb.DuckDBPyConnection | None = None
    try:
        db = initialize()
        register_table(db, budget_data, "budget")

        start = datetime.now(timezone.utc)
        result_data = execute_sql(db, sql)
        elapsed_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

        # Stamp metadata
        now = datetime.now(timezone.utc)
        result_data.metadata = DataMetadata(
            sourceName=budget_data.metadata.sourceName,
            sourceFormat=budget_data.metadata.sourceFormat,
            importedAt=budget_data.metadata.importedAt,
            transformedAt=now,
        )

        return TransformSuccess(data=result_data, executionTimeMs=elapsed_ms)

    except Exception as exc:
        sql_state = ""
        if hasattr(exc, "sqlstate"):
            sql_state = str(exc.sqlstate)
        return TransformError(
            message=f"Transformation failed: {exc}",
            sqlState=sql_state,
        )
    finally:
        if db is not None:
            db.close()


def import_budget_file(
    raw_bytes: bytes,
) -> TabularData | str:
    """Parse an Excel file and extract budget data.

    Returns TabularData on success, or an error message string on failure.
    Records importedAt timestamp in metadata.
    Validates file size before parsing (Req 15.1, 15.2).
    Ensures client-side only processing (Req 13.1, 13.2).
    """
    from src.core.memory import (
        FileSizeError,
        WasmMemoryError,
        assert_client_side_only,
        validate_file_size,
    )
    from src.modules.excel2budget.importer import (
        ParseError,
        extractBudgetData,
        parseExcelFile,
    )

    assert_client_side_only()

    try:
        validate_file_size(raw_bytes)
    except FileSizeError as exc:
        return str(exc)
    except WasmMemoryError as exc:
        return str(exc)

    workbook = parseExcelFile(raw_bytes)
    if isinstance(workbook, ParseError):
        return workbook.message

    budget_data = extractBudgetData(workbook, "Budget")
    if isinstance(budget_data, ParseError):
        return budget_data.message

    # Stamp import time
    budget_data.metadata.importedAt = datetime.now(timezone.utc)
    return budget_data


def export_data(
    data: TabularData,
    file_format: FileFormat,
    template: OutputTemplate | None = None,
) -> bytes:
    """Export TabularData to the specified format.

    Stamps exportedAt in metadata and delegates to the format exporter.
    For Excel export, a template is required to set the sheet name.
    """
    from src.export.exporter import exportToCSV, exportToExcel

    if file_format == FileFormat.CSV:
        return exportToCSV(data)
    elif file_format == FileFormat.EXCEL:
        if template is None:
            template = OutputTemplate(packageName="", templateName="export", columns=[])
        return exportToExcel(data, template)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")
