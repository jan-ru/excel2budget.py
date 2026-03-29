"""Property tests for source immutability, determinism, and invalid DC detection.

**Validates: Requirements 10.1, 10.2, 11.1, 14.1**

Property 8: Source data immutability — budget table unchanged after transformation
Property 9: Transformation determinism — same inputs produce identical output
Property 16: Invalid DC value detection — non-D/C values produce TransformResult.Error
"""

from __future__ import annotations

import copy

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.core.types import (
    ColumnDef,
    DataMetadata,
    DataType,
    FloatVal,
    IntVal,
    MappingConfig,
    MonthColumnDef,
    NullVal,
    Row,
    StringVal,
    TabularData,
    TransformError,
    TransformSuccess,
    UserParams,
)
from src.modules.excel2budget.pipeline import run_budget_transformation
from src.templates.twinfield.budget import TWINFIELD_BUDGET


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_ident_col_name = st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True)


@st.composite
def valid_budget_data(draw: st.DrawFn):
    """Generate valid budget data with all-valid DC values."""
    num_months = draw(st.integers(min_value=1, max_value=4))
    num_rows = draw(st.integers(min_value=1, max_value=6))

    total_cols = 3 + num_months
    col_names = draw(
        st.lists(_ident_col_name, min_size=total_cols, max_size=total_cols, unique=True)
    )

    entity_col = col_names[0]
    account_col = col_names[1]
    dc_col = col_names[2]
    month_col_names = col_names[3:]

    period_numbers = draw(
        st.lists(
            st.integers(min_value=1, max_value=12),
            min_size=num_months,
            max_size=num_months,
            unique=True,
        )
    )

    year = draw(st.integers(min_value=2000, max_value=2100))
    budgetcode = draw(
        st.text(min_size=1, max_size=10)
        .filter(lambda s: s.strip() != "" and "\x00" not in s)
    )

    month_columns = [
        MonthColumnDef(sourceColumnName=name, periodNumber=pn, year=year)
        for name, pn in zip(month_col_names, period_numbers)
    ]

    mapping = MappingConfig(
        entityColumn=entity_col,
        accountColumn=account_col,
        dcColumn=dc_col,
        monthColumns=month_columns,
    )
    params = UserParams(budgetcode=budgetcode, year=year)

    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in col_names]

    rows = []
    for _ in range(num_rows):
        dc_val = draw(st.sampled_from(["D", "C"]))
        values = []
        for col in col_names:
            if col == entity_col:
                values.append(StringVal("E01"))
            elif col == account_col:
                values.append(StringVal("4000"))
            elif col == dc_col:
                values.append(StringVal(dc_val))
            else:
                values.append(FloatVal(draw(
                    st.floats(min_value=-10000, max_value=10000,
                              allow_nan=False, allow_infinity=False)
                )))
        rows.append(Row(values=values))

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata(),
    )

    return data, mapping, params


@st.composite
def budget_data_with_invalid_dc(draw: st.DrawFn):
    """Generate budget data where at least one row has an invalid DC value."""
    num_months = draw(st.integers(min_value=1, max_value=3))
    num_rows = draw(st.integers(min_value=1, max_value=6))

    total_cols = 3 + num_months
    col_names = draw(
        st.lists(_ident_col_name, min_size=total_cols, max_size=total_cols, unique=True)
    )

    entity_col = col_names[0]
    account_col = col_names[1]
    dc_col = col_names[2]
    month_col_names = col_names[3:]

    period_numbers = draw(
        st.lists(
            st.integers(min_value=1, max_value=12),
            min_size=num_months,
            max_size=num_months,
            unique=True,
        )
    )

    year = draw(st.integers(min_value=2000, max_value=2100))
    budgetcode = draw(
        st.text(min_size=1, max_size=10)
        .filter(lambda s: s.strip() != "" and "\x00" not in s)
    )

    month_columns = [
        MonthColumnDef(sourceColumnName=name, periodNumber=pn, year=year)
        for name, pn in zip(month_col_names, period_numbers)
    ]

    mapping = MappingConfig(
        entityColumn=entity_col,
        accountColumn=account_col,
        dcColumn=dc_col,
        monthColumns=month_columns,
    )
    params = UserParams(budgetcode=budgetcode, year=year)

    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in col_names]

    # Invalid DC values (anything other than "D" or "C")
    invalid_dc_values = ["X", "d", "c", "B", "DC", "debit", "credit", "1", ""]

    rows = []
    invalid_positions = []
    for i in range(num_rows):
        # At least one row must have an invalid DC value
        if i == 0:
            dc_val = draw(st.sampled_from(invalid_dc_values))
            invalid_positions.append((i, dc_val))
        else:
            use_invalid = draw(st.booleans())
            if use_invalid:
                dc_val = draw(st.sampled_from(invalid_dc_values))
                invalid_positions.append((i, dc_val))
            else:
                dc_val = draw(st.sampled_from(["D", "C"]))

        values = []
        for col in col_names:
            if col == entity_col:
                values.append(StringVal("E01"))
            elif col == account_col:
                values.append(StringVal("4000"))
            elif col == dc_col:
                values.append(StringVal(dc_val))
            else:
                values.append(FloatVal(100.0))
        rows.append(Row(values=values))

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata(),
    )

    return data, mapping, params, invalid_positions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_compare_tabular(a: TabularData, b: TabularData) -> bool:
    """Compare two TabularData instances for structural equality."""
    if a.rowCount != b.rowCount:
        return False
    if len(a.columns) != len(b.columns):
        return False
    for ca, cb in zip(a.columns, b.columns):
        if ca.name != cb.name or ca.dataType != cb.dataType:
            return False
    if len(a.rows) != len(b.rows):
        return False
    for ra, rb in zip(a.rows, b.rows):
        if len(ra.values) != len(rb.values):
            return False
        for va, vb in zip(ra.values, rb.values):
            if type(va) != type(vb):
                return False
            if isinstance(va, NullVal):
                continue
            if va != vb:
                return False
    return True


def _cell_str(cell) -> str | None:
    if isinstance(cell, NullVal):
        return None
    if isinstance(cell, StringVal):
        return cell.value
    return str(cell)


def _cell_float(cell) -> float | None:
    if isinstance(cell, FloatVal):
        return cell.value
    if isinstance(cell, IntVal):
        return float(cell.value)
    if isinstance(cell, NullVal):
        return None
    return None


# ---------------------------------------------------------------------------
# Property 8: Source data immutability
# ---------------------------------------------------------------------------

@given(data=valid_budget_data())
@settings(max_examples=100, deadline=None)
def test_property_8_source_data_immutability(data):
    """Budget data must be unchanged after transformation.

    **Validates: Requirements 10.1, 10.2**
    """
    budget_data, mapping, params = data

    # Deep copy the source data before transformation
    original = copy.deepcopy(budget_data)

    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess)

    # Source data must be identical to the deep copy
    assert _deep_compare_tabular(budget_data, original), (
        "Source budget data was modified during transformation"
    )


# ---------------------------------------------------------------------------
# Property 9: Transformation determinism
# ---------------------------------------------------------------------------

@given(data=valid_budget_data())
@settings(max_examples=50, deadline=None)
def test_property_9_transformation_determinism(data):
    """Same inputs produce identical output.

    **Validates: Requirement 11.1**
    """
    budget_data, mapping, params = data

    result1 = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    result2 = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)

    assert isinstance(result1, TransformSuccess)
    assert isinstance(result2, TransformSuccess)

    out1 = result1.data
    out2 = result2.data

    # Same row count
    assert out1.rowCount == out2.rowCount, (
        f"Row count differs: {out1.rowCount} vs {out2.rowCount}"
    )

    # Same columns
    assert len(out1.columns) == len(out2.columns)
    for c1, c2 in zip(out1.columns, out2.columns):
        assert c1.name == c2.name

    # Same values
    for i, (r1, r2) in enumerate(zip(out1.rows, out2.rows)):
        for j, (v1, v2) in enumerate(zip(r1.values, r2.values)):
            s1 = _cell_str(v1)
            s2 = _cell_str(v2)
            f1 = _cell_float(v1)
            f2 = _cell_float(v2)
            if f1 is not None and f2 is not None:
                assert f1 == f2, (
                    f"Row {i}, col {j}: {f1} != {f2}"
                )
            else:
                assert s1 == s2, (
                    f"Row {i}, col {j}: '{s1}' != '{s2}'"
                )


# ---------------------------------------------------------------------------
# Property 16: Invalid DC value detection
# ---------------------------------------------------------------------------

@given(data=budget_data_with_invalid_dc())
@settings(max_examples=100, deadline=None)
def test_property_16_invalid_dc_detection(data):
    """Non-D/C values produce TransformResult.Error with row positions.

    **Validates: Requirement 14.1**
    """
    budget_data, mapping, params, invalid_positions = data

    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)

    assert isinstance(result, TransformError), (
        f"Expected TransformError for invalid DC values, got {type(result).__name__}"
    )

    # Error message should mention "Invalid DC"
    assert "Invalid DC" in result.message or "invalid" in result.message.lower(), (
        f"Error message doesn't mention invalid DC: {result.message}"
    )

    # Error message should contain at least one of the invalid values
    for row_idx, val in invalid_positions:
        assert val in result.message or f"row {row_idx}" in result.message, (
            f"Error message doesn't reference invalid value '{val}' "
            f"at row {row_idx}: {result.message}"
        )
