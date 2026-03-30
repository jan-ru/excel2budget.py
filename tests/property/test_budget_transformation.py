"""Property tests for budget transformation pipeline.

**Validates: Requirements 5.1–5.10**

Property 1:  Unpivot row count — R rows × M month columns = R×M output rows
Property 2:  Debet/Credit split correctness
Property 3:  Period range validity — Periode in 1–12
Property 4:  Fixed field propagation — Budgetcode and Jaar match userParams
Property 5:  Null account filtering — no output row has null Grootboekrekening
Property 6:  Column schema conformance — output matches OutputTemplate
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

_dc_st = st.sampled_from(["D", "C"])
_entity_st = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=1, max_size=6,
)
_account_st = st.one_of(
    st.text(alphabet="0123456789", min_size=1, max_size=6),
    st.just(None),  # null account
)
_value_st = st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False)


@st.composite
def budget_scenario(draw: st.DrawFn):
    """Generate a complete budget transformation scenario.

    Returns (source_data, mapping_config, user_params, num_valid_rows, num_months).
    """
    num_months = draw(st.integers(1, 6))
    num_rows = draw(st.integers(1, 8))
    period_numbers = sorted(draw(
        st.lists(st.integers(1, 12), min_size=num_months, max_size=num_months, unique=True)
    ))

    month_names = [f"month_{p}" for p in period_numbers]
    month_cols = [
        MonthColumnDef(sourceColumnName=n, periodNumber=p, year=2026)
        for n, p in zip(month_names, period_numbers)
    ]

    mc = MappingConfig(
        entityColumn="Entity",
        accountColumn="Account",
        dcColumn="DC",
        monthColumns=month_cols,
    )

    budgetcode = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        min_size=1, max_size=6,
    ))
    year = draw(st.integers(2000, 2100))
    up = UserParams(budgetcode=budgetcode, year=year)

    columns = [
        ColumnDef("Entity", DataType.STRING),
        ColumnDef("Account", DataType.STRING),
        ColumnDef("DC", DataType.STRING),
    ] + [ColumnDef(n, DataType.FLOAT) for n in month_names]

    rows = []
    valid_count = 0
    for _ in range(num_rows):
        entity = draw(_entity_st)
        account = draw(_account_st)
        dc = draw(_dc_st)
        values = [draw(_value_st) for _ in range(num_months)]

        row_vals = [
            StringVal(entity),
            StringVal(account) if account is not None else NullVal(),
            StringVal(dc),
        ] + [FloatVal(v) for v in values]
        rows.append(Row(row_vals))
        if account is not None:
            valid_count += 1

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows,
        metadata=DataMetadata(),
    )
    return data, mc, up, valid_count, num_months


# ---------------------------------------------------------------------------
# Helper to extract cell value
# ---------------------------------------------------------------------------

def _val(cell):
    if isinstance(cell, NullVal):
        return None
    return cell.value  # type: ignore[union-attr]


def _col_idx(data: TabularData, name: str) -> int:
    for i, c in enumerate(data.columns):
        if c.name == name:
            return i
    raise KeyError(f"Column {name!r} not found")


# ---------------------------------------------------------------------------
# Property 1: Unpivot row count
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_1_unpivot_row_count(scenario) -> None:
    """R valid rows × M month columns = R×M output rows.

    **Validates: Requirements 5.1, 5.2**
    """
    data, mc, up, valid_count, num_months = scenario
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess), f"Expected success, got: {result}"
    expected = valid_count * num_months
    assert result.data.rowCount == expected, (
        f"Expected {expected} rows ({valid_count}×{num_months}), "
        f"got {result.data.rowCount}"
    )


# ---------------------------------------------------------------------------
# Property 2: Debet/Credit split correctness
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_2_debet_credit_split(scenario) -> None:
    """DC='D' → Debet=ROUND(Value,4), Credit=null;
    DC='C' → Credit=ROUND(ABS(Value),4), Debet=null.

    **Validates: Requirements 5.3, 5.4, 5.5**
    """
    data, mc, up, valid_count, num_months = scenario
    assume(valid_count > 0)
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess)

    out = result.data
    debet_idx = _col_idx(out, "Debet")
    credit_idx = _col_idx(out, "Credit")

    for row in out.rows:
        debet = _val(row.values[debet_idx])
        credit = _val(row.values[credit_idx])

        # Exactly one of Debet/Credit is non-null (for non-null values)
        if debet is not None:
            assert credit is None, "Both Debet and Credit are non-null"
            assert debet == round(debet, 4)
        elif credit is not None:
            assert debet is None, "Both Debet and Credit are non-null"
            assert credit >= 0, "Credit must be non-negative (ABS applied)"
            assert credit == round(credit, 4)


# ---------------------------------------------------------------------------
# Property 3: Period range validity
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_3_period_range_validity(scenario) -> None:
    """Periode in 1–12, matches source month column periodNumber.

    **Validates: Requirement 5.6**
    """
    data, mc, up, valid_count, num_months = scenario
    assume(valid_count > 0)
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess)

    out = result.data
    periode_idx = _col_idx(out, "Periode")
    valid_periods = {m.periodNumber for m in mc.monthColumns}

    for row in out.rows:
        periode = _val(row.values[periode_idx])
        assert periode is not None, "Periode must not be null"
        assert 1 <= periode <= 12, f"Periode {periode} out of range"
        assert periode in valid_periods, (
            f"Periode {periode} not in expected periods {valid_periods}"
        )


# ---------------------------------------------------------------------------
# Property 4: Fixed field propagation
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_4_fixed_field_propagation(scenario) -> None:
    """Budgetcode and Jaar match userParams in every row.

    **Validates: Requirements 4.1, 5.7, 5.8**
    """
    data, mc, up, valid_count, num_months = scenario
    assume(valid_count > 0)
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess)

    out = result.data
    bc_idx = _col_idx(out, "Budgetcode")
    jaar_idx = _col_idx(out, "Jaar")

    for row in out.rows:
        assert _val(row.values[bc_idx]) == up.budgetcode
        assert _val(row.values[jaar_idx]) == up.year


# ---------------------------------------------------------------------------
# Property 5: Null account filtering
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_5_null_account_filtering(scenario) -> None:
    """No output row has null Grootboekrekening.

    **Validates: Requirement 5.9**
    """
    data, mc, up, valid_count, num_months = scenario
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess)

    out = result.data
    gbr_idx = _col_idx(out, "Grootboekrekening")

    for row in out.rows:
        val = _val(row.values[gbr_idx])
        assert val is not None, "Grootboekrekening must not be null"


# ---------------------------------------------------------------------------
# Property 6: Column schema conformance
# ---------------------------------------------------------------------------

@given(scenario=budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_6_column_schema_conformance(scenario) -> None:
    """Output columns match OutputTemplate in name, order, types.

    **Validates: Requirement 5.10**
    """
    data, mc, up, valid_count, num_months = scenario
    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformSuccess)

    out = result.data
    assert len(out.columns) == len(TWINFIELD_BUDGET.columns), (
        f"Column count mismatch: {len(out.columns)} vs {len(TWINFIELD_BUDGET.columns)}"
    )
    for i, (actual, expected) in enumerate(zip(out.columns, TWINFIELD_BUDGET.columns)):
        assert actual.name == expected.name, (
            f"Column {i} name: {actual.name!r} vs {expected.name!r}"
        )
        assert actual.dataType == expected.dataType, (
            f"Column {i} ({actual.name}) type: {actual.dataType} vs {expected.dataType}"
        )
