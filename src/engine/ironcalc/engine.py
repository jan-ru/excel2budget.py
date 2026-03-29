"""IronCalc spreadsheet engine wrapper for the Data Conversion Tool.

Provides spreadsheet rendering for input preview and output review,
cell-level access, and data round-tripping via TabularData.

The wrapper uses the ``ironcalc`` Python package (Rust/WASM bindings).
If the package is not installed, a clear ImportError is raised on first use.

Requirements: 1.4, 8.1
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

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
from src.engine.ironcalc.sanitizer import sanitize_cell_value

# ---------------------------------------------------------------------------
# Lazy import of ironcalc — deferred so the rest of the codebase can be
# loaded and tested even when the native package is not installed.
# ---------------------------------------------------------------------------

_ironcalc = None


def _ensure_ironcalc():
    """Import ironcalc on first use, raising a clear error if missing."""
    global _ironcalc
    if _ironcalc is None:
        try:
            import ironcalc as _ic
            _ironcalc = _ic
        except ImportError as exc:
            raise ImportError(
                "The 'ironcalc' package is required for spreadsheet engine "
                "functionality. Install it with: pip install ironcalc"
            ) from exc
    return _ironcalc


# ---------------------------------------------------------------------------
# Handle types — thin wrappers so callers don't depend on ironcalc internals
# ---------------------------------------------------------------------------


class WorkbookHandle:
    """Opaque handle wrapping an IronCalc Model instance."""

    def __init__(self, model) -> None:
        self._model = model


class SheetHandle:
    """Reference to a specific sheet inside a workbook."""

    def __init__(self, model, sheet_index: int, sheet_name: str) -> None:
        self._model = model
        self.sheet_index = sheet_index
        self.sheet_name = sheet_name


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _python_value_to_cell(value) -> CellValue:
    """Convert a raw Python value (from IronCalc) to a CellValue."""
    if value is None or value == "":
        return NullVal()
    if isinstance(value, bool):
        return BoolVal(value)
    if isinstance(value, int):
        return IntVal(value)
    if isinstance(value, float):
        return FloatVal(value)
    return StringVal(str(value))


def _cell_to_python(cell: CellValue):
    """Convert a CellValue to a plain Python value for IronCalc."""
    if isinstance(cell, StringVal):
        return cell.value
    if isinstance(cell, IntVal):
        return str(cell.value)
    if isinstance(cell, FloatVal):
        return str(cell.value)
    if isinstance(cell, BoolVal):
        return str(cell.value).upper()
    if isinstance(cell, DateVal):
        return cell.value
    if isinstance(cell, NullVal):
        return ""
    raise TypeError(f"Unknown CellValue type: {type(cell)}")


def _infer_datatype(value) -> DataType:
    """Infer a DataType from a raw Python value."""
    if value is None or value == "":
        return DataType.STRING
    if isinstance(value, bool):
        return DataType.BOOLEAN
    if isinstance(value, int):
        return DataType.INTEGER
    if isinstance(value, float):
        return DataType.FLOAT
    return DataType.STRING


def _get_cell_raw(model, sheet_idx: int, row: int, col: int):
    """Read a cell value from the IronCalc model.

    IronCalc's Python API exposes ``get_formatted_cell_value`` which
    returns the display string.  We try ``get_cell_value_by_index``
    first (returns typed value) and fall back to the formatted string.
    """
    try:
        val = model.get_cell_value_by_index(sheet_idx, row, col)
        return val
    except (AttributeError, Exception):
        pass
    try:
        val = model.get_formatted_cell_value(sheet_idx, row, col)
        if val == "":
            return None
        # Attempt numeric conversion
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val
    except (AttributeError, Exception):
        return None


def _detect_dimensions(model, sheet_idx: int) -> Tuple[int, int]:
    """Detect the used range (rows, cols) of a sheet.

    Scans from (1,1) outward until empty rows/columns are found.
    IronCalc uses 1-based indexing.
    """
    max_col = 0
    # Scan first row to find column extent
    for c in range(1, 1000):
        val = _get_cell_raw(model, sheet_idx, 1, c)
        if val is None or val == "":
            break
        max_col = c

    if max_col == 0:
        return 0, 0

    max_row = 0
    for r in range(1, 100_000):
        # Check if entire row is empty by sampling first column
        val = _get_cell_raw(model, sheet_idx, r, 1)
        if val is None or val == "":
            # Double-check: scan all columns in this row
            all_empty = True
            for c in range(2, max_col + 1):
                v = _get_cell_raw(model, sheet_idx, r, c)
                if v is not None and v != "":
                    all_empty = False
                    break
            if all_empty:
                break
        max_row = r

    return max_row, max_col


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_excel_file(raw_bytes: bytes) -> WorkbookHandle:
    """Load an Excel file from raw bytes into IronCalc.

    Returns a WorkbookHandle wrapping the IronCalc Model.

    Raises:
        ImportError: If the ironcalc package is not installed.
        ValueError: If the bytes cannot be parsed as a valid .xlsx file.
    """
    ic = _ensure_ironcalc()
    try:
        model = ic.load_from_xlsx("workbook", raw_bytes)
    except Exception as exc:
        raise ValueError(
            f"Failed to load Excel file: {exc}"
        ) from exc
    return WorkbookHandle(model)


def load_data(data: TabularData, sheet_name: str) -> SheetHandle:
    """Create a new IronCalc workbook and populate it with TabularData.

    This is used to display transformed output data for review.

    Returns a SheetHandle for the populated sheet.
    """
    ic = _ensure_ironcalc()
    model = ic.create("workbook", "en", "UTC")
    sheet_idx = 0

    # Rename default sheet
    try:
        model.set_sheet_name(sheet_idx, sheet_name)
    except (AttributeError, Exception):
        pass  # Some versions may not support renaming

    # Write header row (row 1, 1-based)
    for col_idx, col_def in enumerate(data.columns):
        model.set_user_input(sheet_idx, 1, col_idx + 1, col_def.name)

    # Write data rows (starting at row 2)
    for row_idx, row in enumerate(data.rows):
        for col_idx, cell in enumerate(row.values):
            py_val = _cell_to_python(cell)
            if py_val != "":
                model.set_user_input(
                    sheet_idx, row_idx + 2, col_idx + 1, py_val
                )

    return SheetHandle(model, sheet_idx, sheet_name)


def get_cell_value(
    sheet: SheetHandle, row: int, col: int, *, sanitize: bool = True
) -> CellValue:
    """Read a single cell value from a sheet.

    Parameters:
        sheet: The SheetHandle to read from.
        row: 1-based row index.
        col: 1-based column index.
        sanitize: If True (default), sanitize string values to prevent XSS.

    Returns:
        A CellValue variant.
    """
    raw = _get_cell_raw(sheet._model, sheet.sheet_index, row, col)
    cell = _python_value_to_cell(raw)
    if sanitize and isinstance(cell, StringVal):
        return StringVal(sanitize_cell_value(cell.value))
    return cell


def set_cell_value(
    sheet: SheetHandle, row: int, col: int, value: CellValue
) -> None:
    """Write a single cell value to a sheet.

    Parameters:
        sheet: The SheetHandle to write to.
        row: 1-based row index.
        col: 1-based column index.
        value: The CellValue to write.
    """
    py_val = _cell_to_python(value)
    sheet._model.set_user_input(sheet.sheet_index, row, col, py_val)


def export_sheet_data(
    sheet: SheetHandle, *, sanitize: bool = True
) -> TabularData:
    """Export all data from a sheet back to TabularData.

    Reads the used range, treating row 1 as headers and subsequent
    rows as data.

    Parameters:
        sheet: The SheetHandle to export.
        sanitize: If True (default), sanitize string values.

    Returns:
        A TabularData instance with inferred column types.
    """
    model = sheet._model
    sheet_idx = sheet.sheet_index
    max_row, max_col = _detect_dimensions(model, sheet_idx)

    if max_col == 0:
        return TabularData()

    # Row 1 = headers
    col_names: List[str] = []
    for c in range(1, max_col + 1):
        raw = _get_cell_raw(model, sheet_idx, 1, c)
        name = str(raw) if raw is not None else f"Column{c}"
        if sanitize:
            name = sanitize_cell_value(name)
        col_names.append(name)

    # Infer types from first data row
    col_types: List[DataType] = []
    if max_row >= 2:
        for c in range(1, max_col + 1):
            raw = _get_cell_raw(model, sheet_idx, 2, c)
            col_types.append(_infer_datatype(raw))
    else:
        col_types = [DataType.STRING] * max_col

    columns = [
        ColumnDef(name=col_names[i], dataType=col_types[i])
        for i in range(max_col)
    ]

    # Read data rows (row 2 onward)
    rows: List[Row] = []
    for r in range(2, max_row + 1):
        values: List[CellValue] = []
        for c in range(1, max_col + 1):
            raw = _get_cell_raw(model, sheet_idx, r, c)
            cell = _python_value_to_cell(raw)
            if sanitize and isinstance(cell, StringVal):
                cell = StringVal(sanitize_cell_value(cell.value))
            values.append(cell)
        rows.append(Row(values=values))

    return TabularData(
        columns=columns,
        rows=rows,
        rowCount=len(rows),
        metadata=DataMetadata(sourceName=sheet.sheet_name),
    )


def get_sheet_names(workbook: WorkbookHandle) -> List[str]:
    """Return the list of sheet names in the workbook."""
    model = workbook._model
    names: List[str] = []
    try:
        # IronCalc Python API: iterate sheet indices
        idx = 0
        while True:
            try:
                name = model.get_sheet_name(idx)
                if name is None:
                    break
                names.append(name)
                idx += 1
            except (IndexError, Exception):
                break
    except (AttributeError, Exception):
        pass
    return names


def get_sheet_handle(
    workbook: WorkbookHandle, sheet_name: str
) -> SheetHandle:
    """Get a SheetHandle for a named sheet in the workbook.

    Raises:
        ValueError: If the sheet name is not found.
    """
    names = get_sheet_names(workbook)
    for idx, name in enumerate(names):
        if name == sheet_name:
            return SheetHandle(workbook._model, idx, sheet_name)
    raise ValueError(
        f"Sheet '{sheet_name}' not found. Available sheets: {names}"
    )
