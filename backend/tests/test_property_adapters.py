"""Property 17: Adapter TabularData round-trip preserves data values.

For any valid TabularData with valid MappingConfig and UserParams, converting
to FinancialDocument via tabular_to_financial_document and back to TabularData
via financial_document_to_tabular shall preserve the data values (modulo type
normalisation of cell values to strings).

Feature: financial-domain-model, Property 17
Validates: Requirements 11.3, 11.4, 11.5
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.core.adapters import (
    tabular_to_financial_document,
    financial_document_to_tabular,
)
from backend.app.core.types import (
    ColumnDef,
    DataType,
    FromSource,
    MappingConfig,
    MonthColumnDef,
    NullVal,
    OutputTemplate,
    Row,
    StringVal,
    TabularData,
    TemplateColumnDef,
    UserParams,
)


# ---------------------------------------------------------------------------
# Strategies for generating valid TabularData + MappingConfig pairs
# ---------------------------------------------------------------------------

entity_values = st.sampled_from(["MS", "MH", "EL"])
account_values = st.from_regex(r"[0-9]{4}", fullmatch=True)
dc_values = st.sampled_from(["D", "C"])
amount_values = st.decimals(
    min_value=Decimal("-100000"),
    max_value=Decimal("100000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
years = st.integers(min_value=2020, max_value=2039)
month_counts = st.integers(min_value=1, max_value=12)


@st.composite
def tabular_with_config(draw: st.DrawFn):
    """Generate a (TabularData, MappingConfig, UserParams) triple.

    The TabularData has columns: entity, account, dc, month_1 .. month_N.
    """
    year = draw(years)
    n_months = draw(month_counts)
    n_rows = draw(st.integers(min_value=1, max_value=10))

    # Column definitions
    col_defs = [
        ColumnDef(name="entity", dataType=DataType.STRING),
        ColumnDef(name="account", dataType=DataType.STRING),
        ColumnDef(name="dc", dataType=DataType.STRING),
    ]
    month_col_defs = []
    for m in range(1, n_months + 1):
        col_name = f"month_{m}"
        col_defs.append(ColumnDef(name=col_name, dataType=DataType.FLOAT))
        month_col_defs.append(
            MonthColumnDef(sourceColumnName=col_name, periodNumber=m, year=year),
        )

    # Rows
    rows = []
    for _ in range(n_rows):
        entity = draw(entity_values)
        account = draw(account_values)
        dc = draw(dc_values)
        cells = [
            StringVal(value=entity),
            StringVal(value=account),
            StringVal(value=dc),
        ]
        for _m in range(n_months):
            amt = draw(amount_values)
            cells.append(StringVal(value=str(amt)))
        rows.append(Row(values=cells))

    data = TabularData(
        columns=col_defs,
        rows=rows,
        rowCount=len(rows),
    )
    mapping = MappingConfig(
        entityColumn="entity",
        accountColumn="account",
        dcColumn="dc",
        monthColumns=month_col_defs,
    )
    budgetcode = draw(st.text(min_size=1, max_size=5, alphabet="abcv0123456789"))
    params = UserParams(budgetcode=budgetcode, year=year)

    return data, mapping, params


# ---------------------------------------------------------------------------
# Round-trip output template — mirrors the input structure
# ---------------------------------------------------------------------------


def _round_trip_template(n_months: int, year: int) -> OutputTemplate:
    """Build an OutputTemplate that extracts account, entity, period, amount."""
    cols = [
        TemplateColumnDef(
            name="account",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="account"),
        ),
        TemplateColumnDef(
            name="entity",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="entity"),
        ),
        TemplateColumnDef(
            name="period",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="period"),
        ),
        TemplateColumnDef(
            name="amount",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="amount"),
        ),
    ]
    return OutputTemplate(
        packageName="round_trip",
        templateName="round_trip",
        columns=cols,
    )


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(data=tabular_with_config())
def test_adapter_round_trip_preserves_values(
    data: tuple[TabularData, MappingConfig, UserParams],
) -> None:
    """Property 17: round-trip through adapters preserves data values.

    We convert TabularData → FinancialDocument → TabularData (flat) and verify
    that every (account, entity, period, amount) tuple from the FinancialDocument
    appears in the output TabularData rows.
    """
    tabular, mapping, params = data

    # Forward: TabularData → FinancialDocument
    doc = tabular_to_financial_document(tabular, mapping, params)

    # The number of lines should equal n_rows × n_months
    n_months = len(mapping.monthColumns)
    # Rows with empty account are skipped — all our generated rows have accounts
    expected_line_count = tabular.rowCount * n_months
    assert len(doc.lines) == expected_line_count

    # Reverse: FinancialDocument → TabularData
    template = _round_trip_template(n_months, params.year)
    result = financial_document_to_tabular(doc, template)

    # Output row count must match line count
    assert result.rowCount == len(doc.lines)
    assert len(result.rows) == len(doc.lines)

    # Verify each output row matches the corresponding FinancialLine
    for i, line in enumerate(doc.lines):
        row = result.rows[i]
        vals = row.values
        assert not isinstance(vals[0], NullVal)
        assert vals[0].value == line.account  # type: ignore[union-attr]
        assert not isinstance(vals[1], NullVal)
        assert vals[1].value == line.entity  # type: ignore[union-attr]
        assert not isinstance(vals[2], NullVal)
        assert vals[2].value == line.period  # type: ignore[union-attr]
        assert not isinstance(vals[3], NullVal)
        assert vals[3].value == str(line.amount)  # type: ignore[union-attr]
