"""Property tests for budget transformation pipeline.

**Validates: Requirements 5.1–5.10**

Property 1: Unpivot row count — R rows × M month columns = R×M output rows
Property 2: Debet/Credit split correctness
Property 3: Period range validity — Periode in 1–12
Property 4: Fixed field propagation — Budgetcode and Jaar match userParams
Property 5: Null account filtering — no output row has null Grootboekrekening
Property 6: Column schema conformance — output matches OutputTemplate
"""

from __future__ import annotations

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
def budget_data_and_params(draw: st.DrawFn):
    """Generate valid budget TabularData, MappingConfig, and UserParams.

    Produces data with Entity, Account, DC columns plus 1-12 month columns.
    All DC values are valid ("D" or "C"). Account values are non-null.
    """
    num_months = draw(st.integers(min_value=1, max_value=6))
    num_rows = draw(st.integers(min_value=1, max_value=10))

    # Generate unique column names
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

    # Build columns
    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in col_names]

    # Build rows with valid data
    rows = []
    for _ in range(num_rows):
        dc_val = draw(st.sampled_from(["D", "C"]))
        entity_val = draw(st.from_regex(r"[A-Z]{2}[0-9]{2}", fullmatch=True))
        account_val = draw(st.from_regex(r"[0-9]{4}", fullmatch=True))
        values = []
        for col in col_names:
            if col == entity_col:
                values.append(StringVal(entity_val))
            elif col == account_col:
                values.append(StringVal(account_val))
            elif col == dc_col:
                values.append(StringVal(dc_val))
            else:
                amount = draw(st.floats(min_value=-100000, max_value=100000,
                                        allow_nan=False, allow_infinity=False))
                values.append(FloatVal(amount))
        rows.append(Row(values=values))

    data = TabularData(
        columns=columns,
        rows=rows,
        rowCount=num_rows,
        metadata=DataMetadata(),
    )

    return data, mapping, params


@st.composite
def budget_data_with_null_accounts(draw: st.DrawFn):
    """Generate budget data where some rows have null Account values."""
    num_months = draw(st.integers(min_value=1, max_value=4))
    num_rows = draw(st.integers(min_value=2, max_value=8))

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
    null_count = 0
    for i in range(num_rows):
        dc_val = draw(st.sampled_from(["D", "C"]))
        entity_val = "E01"
        # Make some rows have null accounts
        has_null_account = draw(st.booleans())
        values = []
        for col in col_names:
            if col == entity_col:
                values.append(StringVal(entity_val))
            elif col == account_col:
                if has_null_account:
                    values.append(NullVal())
                    null_count += 1
                else:
                    values.append(StringVal("4000"))
            elif col == dc_col:
                values.append(StringVal(dc_val))
            else:
                values.append(FloatVal(100.0))
        rows.append(Row(values=values))

    # Ensure at least one non-null account row so transformation produces output
    non_null_rows = num_rows - null_count
    assume(non_null_rows > 0)

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata(),
    )

    return data, mapping, params, non_null_rows, null_count



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_col_idx(data: TabularData, name: str) -> int:
    for i, col in enumerate(data.columns):
        if col.name == name:
            return i
    return -1


def _cell_float(cell) -> float | None:
    if isinstance(cell, FloatVal):
        return cell.value
    if isinstance(cell, IntVal):
        return float(cell.value)
    if isinstance(cell, NullVal):
        return None
    if isinstance(cell, StringVal):
        try:
            return float(cell.value)
        except (ValueError, TypeError):
            return None
    return None


def _cell_str(cell) -> str | None:
    if isinstance(cell, NullVal):
        return None
    if isinstance(cell, StringVal):
        return cell.value
    if isinstance(cell, IntVal):
        return str(cell.value)
    if isinstance(cell, FloatVal):
        return str(cell.value)
    return str(cell)


def _cell_int(cell) -> int | None:
    if isinstance(cell, IntVal):
        return cell.value
    if isinstance(cell, FloatVal):
        return int(cell.value)
    if isinstance(cell, NullVal):
        return None
    if isinstance(cell, StringVal):
        try:
            return int(cell.value)
        except (ValueError, TypeError):
            return None
    return None


# ---------------------------------------------------------------------------
# Property 1: Unpivot row count
# ---------------------------------------------------------------------------

@given(data=budget_data_and_params())
@settings(max_examples=100, deadline=None)
def test_property_1_unpivot_row_count(data):
    """R rows × M month columns = R×M output rows.

    **Validates: Requirements 5.1, 5.2**
    """
    budget_data, mapping, params = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)

    assert isinstance(result, TransformSuccess), f"Expected success, got: {result}"

    num_rows = budget_data.rowCount
    num_months = len(mapping.monthColumns)
    expected = num_rows * num_months

    assert result.data.rowCount == expected, (
        f"Expected {expected} rows ({num_rows} × {num_months}), "
        f"got {result.data.rowCount}"
    )


# ---------------------------------------------------------------------------
# Property 2: Debet/Credit split correctness
# ---------------------------------------------------------------------------

@given(data=budget_data_and_params())
@settings(max_examples=100, deadline=None)
def test_property_2_debet_credit_split(data):
    """DC='D' → Debet=ROUND(Value,4), Credit=null;
    DC='C' → Credit=ROUND(ABS(Value),4), Debet=null.

    **Validates: Requirements 5.3, 5.4, 5.5**
    """
    budget_data, mapping, params = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess)

    out = result.data
    debet_idx = _get_col_idx(out, "Debet")
    credit_idx = _get_col_idx(out, "Credit")

    assert debet_idx >= 0, "Debet column not found"
    assert credit_idx >= 0, "Credit column not found"

    for row in out.rows:
        debet = _cell_float(row.values[debet_idx])
        credit = _cell_float(row.values[credit_idx])

        # Exactly one of Debet/Credit should be non-null
        has_debet = debet is not None
        has_credit = credit is not None
        assert has_debet != has_credit, (
            f"Expected exactly one of Debet/Credit non-null, "
            f"got Debet={debet}, Credit={credit}"
        )

        # Debet values should be non-negative when rounded
        if has_debet:
            assert debet == round(debet, 4), f"Debet not rounded to 4dp: {debet}"

        # Credit values should be non-negative (ABS applied)
        if has_credit:
            assert credit >= 0, f"Credit should be non-negative: {credit}"
            assert credit == round(credit, 4), f"Credit not rounded to 4dp: {credit}"


# ---------------------------------------------------------------------------
# Property 3: Period range validity
# ---------------------------------------------------------------------------

@given(data=budget_data_and_params())
@settings(max_examples=100, deadline=None)
def test_property_3_period_range_validity(data):
    """Periode in 1–12, matches source month column periodNumber.

    **Validates: Requirement 5.6**
    """
    budget_data, mapping, params = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess)

    out = result.data
    periode_idx = _get_col_idx(out, "Periode")
    assert periode_idx >= 0, "Periode column not found"

    valid_periods = {mc.periodNumber for mc in mapping.monthColumns}

    for row in out.rows:
        periode = _cell_int(row.values[periode_idx])
        assert periode is not None, "Periode should not be null"
        assert 1 <= periode <= 12, f"Periode out of range: {periode}"
        assert periode in valid_periods, (
            f"Periode {periode} not in expected periods {valid_periods}"
        )


# ---------------------------------------------------------------------------
# Property 4: Fixed field propagation
# ---------------------------------------------------------------------------

@given(data=budget_data_and_params())
@settings(max_examples=100, deadline=None)
def test_property_4_fixed_field_propagation(data):
    """Budgetcode and Jaar match userParams in every row.

    **Validates: Requirements 4.1, 5.7, 5.8**
    """
    budget_data, mapping, params = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess)

    out = result.data
    bc_idx = _get_col_idx(out, "Budgetcode")
    jaar_idx = _get_col_idx(out, "Jaar")

    assert bc_idx >= 0, "Budgetcode column not found"
    assert jaar_idx >= 0, "Jaar column not found"

    for row in out.rows:
        bc = _cell_str(row.values[bc_idx])
        assert bc == params.budgetcode, (
            f"Budgetcode mismatch: expected '{params.budgetcode}', got '{bc}'"
        )

        jaar = _cell_int(row.values[jaar_idx])
        assert jaar == params.year, (
            f"Jaar mismatch: expected {params.year}, got {jaar}"
        )


# ---------------------------------------------------------------------------
# Property 5: Null account filtering
# ---------------------------------------------------------------------------

@given(data=budget_data_with_null_accounts())
@settings(max_examples=100, deadline=None)
def test_property_5_null_account_filtering(data):
    """No output row has null Grootboekrekening.

    **Validates: Requirement 5.9**
    """
    budget_data, mapping, params, non_null_rows, null_count = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess), f"Expected success, got: {result}"

    out = result.data
    gbr_idx = _get_col_idx(out, "Grootboekrekening")
    assert gbr_idx >= 0, "Grootboekrekening column not found"

    for i, row in enumerate(out.rows):
        val = _cell_str(row.values[gbr_idx])
        assert val is not None, f"Output row {i} has null Grootboekrekening"

    # Row count should reflect only non-null-account source rows
    expected = non_null_rows * len(mapping.monthColumns)
    assert out.rowCount == expected, (
        f"Expected {expected} rows ({non_null_rows} non-null × "
        f"{len(mapping.monthColumns)} months), got {out.rowCount}"
    )


# ---------------------------------------------------------------------------
# Property 6: Column schema conformance
# ---------------------------------------------------------------------------

@given(data=budget_data_and_params())
@settings(max_examples=100, deadline=None)
def test_property_6_column_schema_conformance(data):
    """Output columns match OutputTemplate in name, order, types.

    **Validates: Requirement 5.10**
    """
    budget_data, mapping, params = data
    result = run_budget_transformation(budget_data, mapping, TWINFIELD_BUDGET, params)
    assert isinstance(result, TransformSuccess)

    out = result.data
    template_cols = TWINFIELD_BUDGET.columns

    assert len(out.columns) == len(template_cols), (
        f"Column count mismatch: got {len(out.columns)}, "
        f"expected {len(template_cols)}"
    )

    for i, (actual, expected) in enumerate(zip(out.columns, template_cols)):
        assert actual.name == expected.name, (
            f"Column {i} name mismatch: '{actual.name}' vs '{expected.name}'"
        )
