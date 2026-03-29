"""Property tests for date display and date stamping.

**Validates: Requirements 18.1, 18.2, 19.1, 19.2, 19.3**

Property 22: Date presence on all screens — every rendered screen includes a visible date
Property 23: Data date stamping completeness — metadata contains importedAt, transformedAt, exportedAt at appropriate stages
"""

from __future__ import annotations

import re
from io import BytesIO

from hypothesis import given, settings
from hypothesis import strategies as st
from openpyxl import Workbook

from src.ui.app import BudgetConversionApp, Screen
from src.core.types import (
    TabularData,
    DataMetadata,
    ColumnDef,
    Row,
    DataType,
    FileFormat,
    MappingConfig,
    MonthColumnDef,
    UserParams,
    OutputTemplate,
    StringVal,
    IntVal,
    FloatVal,
    NullVal,
    TransformSuccess,
)
from src.modules.excel2budget.pipeline import (
    import_budget_file,
    run_budget_transformation,
    export_data,
)
from src.templates.twinfield.budget import TWINFIELD_BUDGET


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ALL_SCREENS = [
    Screen.UPLOAD,
    Screen.PREVIEW,
    Screen.CONFIGURATION,
    Screen.TRANSFORM,
    Screen.OUTPUT,
    Screen.DOCUMENTATION,
]

_SCREEN_RENDER_MAP = {
    Screen.UPLOAD: "render_upload_screen",
    Screen.PREVIEW: "render_preview_screen",
    Screen.CONFIGURATION: "render_configuration_screen",
    Screen.TRANSFORM: "render_transform_screen",
    Screen.OUTPUT: "render_output_screen",
    Screen.DOCUMENTATION: "render_documentation_screen",
}


def _make_budget_xlsx() -> bytes:
    """Create a minimal valid budget .xlsx file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Budget"
    ws.append(["Entity", "Account", "DC", "jan-26", "feb-26"])
    ws.append(["NL01", "4000", "D", 1000.0, 2000.0])
    ws.append(["NL01", "5000", "C", 500.0, 600.0])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Property 22: Date presence on all screens
# ---------------------------------------------------------------------------


@given(screen=st.sampled_from(_ALL_SCREENS))
@settings(max_examples=20)
def test_property_22_date_presence_on_all_screens(screen: Screen):
    """Every rendered screen includes a non-empty current_date in YYYY-MM-DD
    format and has pdf_action_available set to True.

    **Validates: Requirements 18.1, 18.2**
    """
    app = BudgetConversionApp()
    render_method = getattr(app, _SCREEN_RENDER_MAP[screen])
    content = render_method()

    # current_date must be non-empty
    assert content.current_date, (
        f"Screen {screen.value} has empty current_date"
    )

    # Must be exactly 10 characters in YYYY-MM-DD format
    assert len(content.current_date) == 10, (
        f"Screen {screen.value} date '{content.current_date}' is not 10 chars"
    )
    assert _DATE_PATTERN.match(content.current_date), (
        f"Screen {screen.value} date '{content.current_date}' "
        f"does not match YYYY-MM-DD pattern"
    )

    # PDF action must be available on every screen
    assert content.pdf_action_available is True, (
        f"Screen {screen.value} does not have pdf_action_available=True"
    )


# ---------------------------------------------------------------------------
# Property 23: Data date stamping completeness
# ---------------------------------------------------------------------------


@given(
    dc_val=st.sampled_from(["D", "C"]),
    amount=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=10, deadline=None)
def test_property_23_import_stamps_imported_at(dc_val: str, amount: float):
    """After import_budget_file(), the returned TabularData has
    metadata.importedAt set (not None).

    **Validates: Requirement 19.1**
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Budget"
    ws.append(["Entity", "Account", "DC", "jan-26"])
    ws.append(["NL01", "4000", dc_val, amount])
    buf = BytesIO()
    wb.save(buf)
    raw = buf.getvalue()

    result = import_budget_file(raw)
    assert isinstance(result, TabularData), f"Import failed: {result}"
    assert result.metadata.importedAt is not None, (
        "importedAt should be set after import_budget_file()"
    )


@given(
    dc_val=st.sampled_from(["D", "C"]),
    amount=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
    budgetcode=st.text(min_size=1, max_size=5).filter(lambda s: s.strip() != "" and "\x00" not in s),
    year=st.integers(min_value=2000, max_value=2100),
)
@settings(max_examples=10, deadline=None)
def test_property_23_transform_stamps_transformed_at(
    dc_val: str, amount: float, budgetcode: str, year: int
):
    """After run_budget_transformation(), the result's metadata.transformedAt
    is set (not None).

    **Validates: Requirement 19.2**
    """
    columns = [
        ColumnDef(name="entity", dataType=DataType.STRING),
        ColumnDef(name="account", dataType=DataType.STRING),
        ColumnDef(name="dc", dataType=DataType.STRING),
        ColumnDef(name="jan", dataType=DataType.FLOAT),
    ]
    rows = [
        Row(values=[StringVal("NL01"), StringVal("4000"), StringVal(dc_val), FloatVal(amount)])
    ]
    data = TabularData(columns=columns, rows=rows, rowCount=1, metadata=DataMetadata())

    mapping = MappingConfig(
        entityColumn="entity",
        accountColumn="account",
        dcColumn="dc",
        monthColumns=[MonthColumnDef(sourceColumnName="jan", periodNumber=1, year=year)],
    )
    params = UserParams(budgetcode=budgetcode, year=year)

    result = run_budget_transformation(data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess), f"Transform failed: {result}"
    assert result.data.metadata.transformedAt is not None, (
        "transformedAt should be set after run_budget_transformation()"
    )


@given(
    file_format=st.sampled_from([FileFormat.CSV, FileFormat.EXCEL]),
)
@settings(max_examples=10, deadline=None)
def test_property_23_export_stamps_exported_at(file_format: FileFormat):
    """After exportToCSV() or exportToExcel(), the data's metadata.exportedAt
    is set (not None).

    **Validates: Requirement 19.3**
    """
    columns = [
        ColumnDef(name="Entity", dataType=DataType.STRING),
        ColumnDef(name="Value", dataType=DataType.FLOAT),
    ]
    rows = [Row(values=[StringVal("NL01"), FloatVal(100.0)])]
    data = TabularData(columns=columns, rows=rows, rowCount=1, metadata=DataMetadata())

    result_bytes = export_data(data, file_format)
    assert isinstance(result_bytes, bytes) and len(result_bytes) > 0
    assert data.metadata.exportedAt is not None, (
        f"exportedAt should be set after export_data({file_format.value})"
    )
