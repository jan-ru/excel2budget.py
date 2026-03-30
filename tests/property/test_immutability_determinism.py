"""Property tests for source immutability, determinism, and invalid DC detection.

**Validates: Requirements 10.1, 10.2, 11.1, 14.1**

Property 8:  Source data immutability — budget table unchanged after transformation
Property 9:  Transformation determinism — same inputs produce identical output
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
from src.engine.duckdb.engine import (
    execute_sql,
    execute_sql_typed,
    initialize,
    register_table,
)
from src.modules.excel2budget.pipeline import run_budget_transformation
from src.modules.excel2budget.sql_generator import generate_transform_sql
from src.templates.twinfield.budget import TWINFIELD_BUDGET


# ---------------------------------------------------------------------------
# Strategies (reused from test_budget_transformation)
# ---------------------------------------------------------------------------

_dc_st = st.sampled_from(["D", "C"])
_entity_st = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=1, max_size=6,
)

_account_st = st.text(alphabet="0123456789", min_size=1, max_size=6)
_value_st = st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False)


@st.composite
def valid_budget_scenario(draw: st.DrawFn):
    """Generate a budget scenario with only valid rows (no null accounts)."""
    num_months = draw(st.integers(1, 4))
    num_rows = draw(st.integers(1, 5))
    period_numbers = sorted(draw(
        st.lists(st.integers(1, 12), min_size=num_months, max_size=num_months, unique=True)
    ))
    month_names = [f"month_{p}" for p in period_numbers]
    month_cols = [
        MonthColumnDef(sourceColumnName=n, periodNumber=p, year=2026)
        for n, p in zip(month_names, period_numbers)
    ]
    mc = MappingConfig(
        entityColumn="Entity", accountColumn="Account", dcColumn="DC",
        monthColumns=month_cols,
    )
    budgetcode = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=6,
    ))
    up = UserParams(budgetcode=budgetcode, year=draw(st.integers(2000, 2100)))

    columns = [
        ColumnDef("Entity", DataType.STRING),
        ColumnDef("Account", DataType.STRING),
        ColumnDef("DC", DataType.STRING),
    ] + [ColumnDef(n, DataType.FLOAT) for n in month_names]

    rows = []
    for _ in range(num_rows):
        row_vals = [
            StringVal(draw(_entity_st)),
            StringVal(draw(_account_st)),
            StringVal(draw(_dc_st)),
        ] + [FloatVal(draw(_value_st)) for _ in range(num_months)]
        rows.append(Row(row_vals))

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata(),
    )
    return data, mc, up


def _val(cell):
    if isinstance(cell, NullVal):
        return None
    return cell.value  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Property 8: Source data immutability
# ---------------------------------------------------------------------------

@given(scenario=valid_budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_8_source_data_immutability(scenario) -> None:
    """Budget table in DuckDB is unchanged after transformation.

    **Validates: Requirements 10.1, 10.2**
    """
    data, mc, up = scenario

    db = initialize()
    try:
        # Register and snapshot the source data
        register_table(db, data, "budget")
        before = execute_sql_typed(
            db,
            'SELECT * FROM "budget"',
            data.columns,
        )

        # Run transformation SQL (reads from budget, writes to nothing)
        sql = generate_transform_sql(mc, TWINFIELD_BUDGET, up)
        execute_sql(db, sql)

        # Verify source table is unchanged
        after = execute_sql_typed(
            db,
            'SELECT * FROM "budget"',
            data.columns,
        )

        assert before.rowCount == after.rowCount
        assert len(before.columns) == len(after.columns)
        for br, ar in zip(before.rows, after.rows):
            for bv, av in zip(br.values, ar.values):
                assert type(bv) is type(av)
                assert _val(bv) == _val(av) or (
                    isinstance(bv, FloatVal) and isinstance(av, FloatVal)
                    and abs(bv.value - av.value) < 1e-9
                )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 9: Transformation determinism
# ---------------------------------------------------------------------------

@given(scenario=valid_budget_scenario())
@settings(max_examples=200, deadline=None)
def test_property_9_transformation_determinism(scenario) -> None:
    """Same inputs produce identical output on every execution.

    **Validates: Requirement 11.1**
    """
    data, mc, up = scenario

    result1 = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    result2 = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)

    assert isinstance(result1, TransformSuccess)
    assert isinstance(result2, TransformSuccess)

    out1 = result1.data
    out2 = result2.data

    assert out1.rowCount == out2.rowCount
    assert len(out1.columns) == len(out2.columns)

    for c1, c2 in zip(out1.columns, out2.columns):
        assert c1.name == c2.name
        assert c1.dataType == c2.dataType

    for r1, r2 in zip(out1.rows, out2.rows):
        for v1, v2 in zip(r1.values, r2.values):
            val1, val2 = _val(v1), _val(v2)
            if isinstance(val1, float) and isinstance(val2, float):
                assert abs(val1 - val2) < 1e-9
            else:
                assert val1 == val2


# ---------------------------------------------------------------------------
# Property 16: Invalid DC value detection
# ---------------------------------------------------------------------------

_invalid_dc_st = st.text(min_size=1, max_size=5).filter(
    lambda s: s not in ("D", "C")
)


@st.composite
def budget_with_invalid_dc(draw: st.DrawFn):
    """Generate budget data containing at least one invalid DC value."""
    num_months = draw(st.integers(1, 3))
    period_numbers = sorted(draw(
        st.lists(st.integers(1, 12), min_size=num_months, max_size=num_months, unique=True)
    ))
    month_names = [f"month_{p}" for p in period_numbers]
    month_cols = [
        MonthColumnDef(sourceColumnName=n, periodNumber=p, year=2026)
        for n, p in zip(month_names, period_numbers)
    ]
    mc = MappingConfig(
        entityColumn="Entity", accountColumn="Account", dcColumn="DC",
        monthColumns=month_cols,
    )
    up = UserParams(budgetcode="010", year=2026)

    columns = [
        ColumnDef("Entity", DataType.STRING),
        ColumnDef("Account", DataType.STRING),
        ColumnDef("DC", DataType.STRING),
    ] + [ColumnDef(n, DataType.FLOAT) for n in month_names]

    # At least one row with invalid DC
    num_rows = draw(st.integers(1, 5))
    invalid_row_idx = draw(st.integers(0, num_rows - 1))

    rows = []
    for i in range(num_rows):
        dc = draw(_invalid_dc_st) if i == invalid_row_idx else draw(_dc_st)
        row_vals = [
            StringVal(draw(_entity_st)),
            StringVal(draw(_account_st)),
            StringVal(dc),
        ] + [FloatVal(draw(_value_st)) for _ in range(num_months)]
        rows.append(Row(row_vals))

    data = TabularData(
        columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata(),
    )
    return data, mc, up, invalid_row_idx


@given(scenario=budget_with_invalid_dc())
@settings(max_examples=200, deadline=None)
def test_property_16_invalid_dc_detection(scenario) -> None:
    """Non-D/C values produce TransformResult.Error with row positions.

    **Validates: Requirement 14.1**
    """
    data, mc, up, invalid_row_idx = scenario

    result = run_budget_transformation(data, mc, TWINFIELD_BUDGET, up)
    assert isinstance(result, TransformError), (
        f"Expected TransformError for invalid DC, got {type(result).__name__}"
    )
    assert "Invalid DC values" in result.message
    assert f"row {invalid_row_idx}" in result.message
