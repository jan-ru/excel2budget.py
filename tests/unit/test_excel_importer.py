"""Unit tests for the Excel budget importer.

Tests cover:
- Valid .xlsx parsing
- Missing Budget sheet error
- Invalid file format error
- Mapping extraction with valid and invalid column layouts
- Month column detection with various naming conventions
"""

from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook

from src.core.types import (
    ColumnDef,
    DataType,
    FloatVal,
    IntVal,
    MappingConfig,
    MonthColumnDef,
    NullVal,
    Row,
    StringVal,
    TabularData,
)
from src.modules.excel2budget.importer import (
    MappingError,
    ParseError,
    detectMonthColumns,
    extractBudgetData,
    extractMappingConfig,
    parseExcelFile,
)


# --- Helpers ---


def _make_budget_workbook(
    headers: list[str],
    rows: list[list],
    sheet_name: str = "Budget",
) -> bytes:
    """Create an in-memory .xlsx with the given headers and rows."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _standard_headers() -> list[str]:
    return ["Entity", "Account", "DC", "jan-26", "feb-26", "mrt-26"]


def _standard_rows() -> list[list]:
    return [
        ["NL01", "4000", "D", 1000.0, 2000.0, 3000.0],
        ["NL01", "5000", "C", 500.0, 600.0, 700.0],
    ]


# --- parseExcelFile tests ---


class TestParseExcelFile:
    def test_valid_xlsx(self):
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        result = parseExcelFile(raw)
        assert isinstance(result, Workbook)

    def test_invalid_bytes(self):
        result = parseExcelFile(b"this is not an xlsx file")
        assert isinstance(result, ParseError)
        assert ".xlsx" in result.message

    def test_empty_bytes(self):
        result = parseExcelFile(b"")
        assert isinstance(result, ParseError)

    def test_parse_error_has_empty_sheets(self):
        """ParseError for invalid files has empty available_sheets."""
        result = parseExcelFile(b"not xlsx")
        assert isinstance(result, ParseError)
        assert result.available_sheets == []


# --- extractBudgetData tests ---


class TestExtractBudgetData:
    def test_valid_budget_sheet(self):
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        assert result.rowCount == 2
        assert len(result.columns) == 6
        assert result.columns[0].name == "Entity"
        assert result.columns[3].name == "jan-26"

    def test_missing_budget_sheet(self):
        raw = _make_budget_workbook(
            ["A", "B"], [[1, 2]], sheet_name="OtherSheet"
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractBudgetData(wb, "Budget")
        assert isinstance(result, ParseError)
        assert "Budget" in result.message
        assert "OtherSheet" in result.available_sheets

    def test_custom_sheet_name(self):
        raw = _make_budget_workbook(
            _standard_headers(), _standard_rows(), sheet_name="MyBudget"
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractBudgetData(wb, "MyBudget")
        assert isinstance(result, TabularData)
        assert result.rowCount == 2

    def test_empty_sheet(self):
        wb_obj = Workbook()
        ws = wb_obj.active
        ws.title = "Budget"
        buf = BytesIO()
        wb_obj.save(buf)
        raw = buf.getvalue()

        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, ParseError)
        assert "empty" in result.message.lower()

    def test_null_values_preserved(self):
        raw = _make_budget_workbook(
            _standard_headers(),
            [["NL01", None, "D", 100.0, None, 300.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        row = result.rows[0]
        assert isinstance(row.values[1], NullVal)
        assert isinstance(row.values[4], NullVal)


# --- extractMappingConfig tests ---


class TestExtractMappingConfig:
    def test_valid_mapping(self):
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert result.entityColumn == "Entity"
        assert result.accountColumn == "Account"
        assert result.dcColumn == "DC"
        assert len(result.monthColumns) == 3
        periods = [mc.periodNumber for mc in result.monthColumns]
        assert periods == [1, 2, 3]

    def test_missing_entity_column(self):
        raw = _make_budget_workbook(
            ["Name", "Account", "DC", "jan-26"],
            [["NL01", "4000", "D", 100.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingError)
        assert "Entity" in result.missing_columns
        assert "Name" in result.available_columns

    def test_missing_multiple_columns(self):
        raw = _make_budget_workbook(
            ["Name", "Code", "Flag", "jan-26"],
            [["NL01", "4000", "D", 100.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingError)
        assert len(result.missing_columns) == 3

    def test_no_month_columns(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "Amount"],
            [["NL01", "4000", "D", 100.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingError)
        assert "month" in result.message.lower()

    def test_case_insensitive_required_columns(self):
        raw = _make_budget_workbook(
            ["entity", "account", "dc", "jan-26"],
            [["NL01", "4000", "D", 100.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert result.entityColumn == "entity"
        assert result.accountColumn == "account"
        assert result.dcColumn == "dc"

    def test_twelve_month_columns(self):
        months = [f"{m}-26" for m in [
            "jan", "feb", "mrt", "apr", "mei", "jun",
            "jul", "aug", "sep", "okt", "nov", "dec",
        ]]
        headers = ["Entity", "Account", "DC"] + months
        row_data = ["NL01", "4000", "D"] + [100.0] * 12
        raw = _make_budget_workbook(headers, [row_data])
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert len(result.monthColumns) == 12
        periods = [mc.periodNumber for mc in result.monthColumns]
        assert periods == list(range(1, 13))

    def test_four_digit_year_in_month_columns(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-2026", "feb-2026"],
            [["NL01", "4000", "D", 100.0, 200.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert len(result.monthColumns) == 2
        assert result.monthColumns[0].year == 2026
        assert result.monthColumns[1].year == 2026

    def test_missing_sheet_returns_mapping_error(self):
        raw = _make_budget_workbook(
            _standard_headers(), _standard_rows(), sheet_name="Other"
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb, "Budget")
        assert isinstance(result, MappingError)


# --- detectMonthColumns tests ---


class TestDetectMonthColumns:
    def test_valid_month_columns(self):
        data = TabularData(
            columns=[
                ColumnDef(name="Entity", dataType=DataType.STRING),
                ColumnDef(name="Account", dataType=DataType.STRING),
                ColumnDef(name="DC", dataType=DataType.STRING),
                ColumnDef(name="jan-26", dataType=DataType.FLOAT),
                ColumnDef(name="feb-26", dataType=DataType.FLOAT),
            ],
            rows=[],
            rowCount=0,
        )
        config = MappingConfig(
            entityColumn="Entity",
            accountColumn="Account",
            dcColumn="DC",
            monthColumns=[
                MonthColumnDef(sourceColumnName="jan-26", periodNumber=1, year=2026),
                MonthColumnDef(sourceColumnName="feb-26", periodNumber=2, year=2026),
            ],
        )
        result = detectMonthColumns(data, config)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_missing_month_column_in_data(self):
        data = TabularData(
            columns=[
                ColumnDef(name="Entity", dataType=DataType.STRING),
                ColumnDef(name="Account", dataType=DataType.STRING),
                ColumnDef(name="DC", dataType=DataType.STRING),
                ColumnDef(name="jan-26", dataType=DataType.FLOAT),
            ],
            rows=[],
            rowCount=0,
        )
        config = MappingConfig(
            entityColumn="Entity",
            accountColumn="Account",
            dcColumn="DC",
            monthColumns=[
                MonthColumnDef(sourceColumnName="jan-26", periodNumber=1, year=2026),
                MonthColumnDef(sourceColumnName="feb-26", periodNumber=2, year=2026),
            ],
        )
        result = detectMonthColumns(data, config)
        assert isinstance(result, MappingError)
        assert "feb-26" in result.missing_columns

    def test_all_month_columns_present(self):
        """When all referenced month columns exist, returns the list."""
        data = TabularData(
            columns=[
                ColumnDef(name="Entity", dataType=DataType.STRING),
                ColumnDef(name="Account", dataType=DataType.STRING),
                ColumnDef(name="DC", dataType=DataType.STRING),
                ColumnDef(name="jan-26", dataType=DataType.FLOAT),
                ColumnDef(name="feb-26", dataType=DataType.FLOAT),
                ColumnDef(name="mrt-26", dataType=DataType.FLOAT),
            ],
            rows=[],
            rowCount=0,
        )
        config = MappingConfig(
            entityColumn="Entity",
            accountColumn="Account",
            dcColumn="DC",
            monthColumns=[
                MonthColumnDef(sourceColumnName="jan-26", periodNumber=1, year=2026),
                MonthColumnDef(sourceColumnName="feb-26", periodNumber=2, year=2026),
                MonthColumnDef(sourceColumnName="mrt-26", periodNumber=3, year=2026),
            ],
        )
        result = detectMonthColumns(data, config)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_missing_columns_lists_available(self):
        """MappingError includes available_columns when month columns are missing."""
        data = TabularData(
            columns=[
                ColumnDef(name="Entity", dataType=DataType.STRING),
                ColumnDef(name="Account", dataType=DataType.STRING),
                ColumnDef(name="DC", dataType=DataType.STRING),
            ],
            rows=[],
            rowCount=0,
        )
        config = MappingConfig(
            entityColumn="Entity",
            accountColumn="Account",
            dcColumn="DC",
            monthColumns=[
                MonthColumnDef(sourceColumnName="jan-26", periodNumber=1, year=2026),
            ],
        )
        result = detectMonthColumns(data, config)
        assert isinstance(result, MappingError)
        assert "jan-26" in result.missing_columns
        assert "Entity" in result.available_columns
        assert "Account" in result.available_columns


# --- Month column naming convention tests ---


class TestMonthColumnNaming:
    """Test various month column naming patterns."""

    def test_standard_dutch_months(self):
        """All 12 Dutch month abbreviations are recognized."""
        months = [
            "jan", "feb", "mrt", "apr", "mei", "jun",
            "jul", "aug", "sep", "okt", "nov", "dec",
        ]
        headers = ["Entity", "Account", "DC"] + [f"{m}-26" for m in months]
        raw = _make_budget_workbook(headers, [["NL01", "4000", "D"] + [0.0] * 12])
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert len(result.monthColumns) == 12

    def test_mixed_case_months(self):
        """Month names with different casing are recognized."""
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "Jan-26", "FEB-26", "MRT-26"],
            [["NL01", "4000", "D", 1.0, 2.0, 3.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert len(result.monthColumns) == 3

    def test_two_digit_year(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-24"],
            [["NL01", "4000", "D", 100.0]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert result.monthColumns[0].year == 2024

    def test_non_month_columns_ignored(self):
        """Columns that don't match the month pattern are not detected as months."""
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-26", "Total", "Notes"],
            [["NL01", "4000", "D", 100.0, 100.0, "test"]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        result = extractMappingConfig(wb)
        assert isinstance(result, MappingConfig)
        assert len(result.monthColumns) == 1
        assert result.monthColumns[0].sourceColumnName == "jan-26"


class TestExtractBudgetDataTypes:
    """Test cell value type conversion in extractBudgetData."""

    def test_integer_values(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-26"],
            [["NL01", "4000", "D", 1000]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        # openpyxl may return int or float; importer maps both
        val = result.rows[0].values[3]
        assert isinstance(val, (IntVal, FloatVal))

    def test_float_values(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-26"],
            [["NL01", "4000", "D", 1234.56]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        val = result.rows[0].values[3]
        assert isinstance(val, FloatVal)
        assert val.value == pytest.approx(1234.56)

    def test_string_values(self):
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-26"],
            [["NL01", "4000", "D", "text"]],
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        val = result.rows[0].values[3]
        assert isinstance(val, StringVal)
        assert val.value == "text"

    def test_row_count_matches_data(self):
        """rowCount field matches the actual number of data rows."""
        rows = [["NL01", "4000", "D", float(i)] for i in range(5)]
        raw = _make_budget_workbook(
            ["Entity", "Account", "DC", "jan-26"], rows
        )
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        assert result.rowCount == 5
        assert len(result.rows) == 5

    def test_column_count_matches_header(self):
        """Each row has exactly as many values as there are columns."""
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        for row in result.rows:
            assert len(row.values) == len(result.columns)

    def test_metadata_source_name(self):
        """Metadata records the sheet name as sourceName."""
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)
        result = extractBudgetData(wb)
        assert isinstance(result, TabularData)
        assert result.metadata.sourceName == "Budget"


class TestEndToEndColumnValidation:
    """Test that extractMappingConfig + detectMonthColumns together
    ensure all referenced columns exist in the budget data (Req 2.5)."""

    def test_mapping_columns_exist_in_budget_data(self):
        """All columns referenced by MappingConfig exist in extracted TabularData."""
        raw = _make_budget_workbook(_standard_headers(), _standard_rows())
        wb = parseExcelFile(raw)
        assert isinstance(wb, Workbook)

        data = extractBudgetData(wb)
        assert isinstance(data, TabularData)

        # Re-parse since read_only workbook may be consumed
        wb2 = parseExcelFile(raw)
        assert isinstance(wb2, Workbook)
        config = extractMappingConfig(wb2)
        assert isinstance(config, MappingConfig)

        # Verify entity/account/dc columns exist in data
        col_names = {col.name for col in data.columns}
        assert config.entityColumn in col_names
        assert config.accountColumn in col_names
        assert config.dcColumn in col_names

        # Verify month columns exist via detectMonthColumns
        result = detectMonthColumns(data, config)
        assert isinstance(result, list)
        assert len(result) == len(config.monthColumns)
