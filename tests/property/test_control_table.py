"""Property tests for control table generation.

Property 20: Control table balance — all balanceChecks have passed=true
Property 21: Control table row count consistency — outputRowCount = inputRowCount × monthColumnCount

Validates: Requirements 17.6.2, 17.6.3, 17.6.4, 17.6.5, 5.2
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    ColumnDef,
    ConversionConfiguration,
    DataMetadata,
    DataType,
    FloatVal,
    MappingConfig,
    MonthColumnDef,
    NullVal,
    Row,
    StringVal,
    TabularData,
    TransformSuccess,
    UserParams,
)
from src.documentation.control_table import generate_control_table
from src.modules.excel2budget.context_builder import build_application_context
from src.modules.excel2budget.pipeline import run_budget_transformation
from src.templates.twinfield.budget import TWINFIELD_BUDGET


_ident_col_name = st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True)


@st.composite
def budget_data_and_params(draw: st.DrawFn):
    """Generate valid budget TabularData, MappingConfig, and UserParams."""
    num_months = draw(st.integers(min_value=1, max_value=6))
    num_rows = draw(st.integers(min_value=1, max_value=10))

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


def _run_and_build_context(data, mapping, params):
    """Run transformation and build ApplicationContext. Returns None on error."""
    result = run_budget_transformation(data, mapping, TWINFIELD_BUDGET, params)
    if not isinstance(result, TransformSuccess):
        return None

    config = ConversionConfiguration(
        packageName="twinfield",
        templateName="budget",
        mappingConfig=mapping,
        userParams=params,
        sourceFileName="test.xlsx",
    )
    context = build_application_context(
        config, data, result.data, mapping, TWINFIELD_BUDGET, "SELECT ..."
    )
    return context


@given(data=budget_data_and_params())
@settings(max_examples=50, deadline=None)
def test_property_20_control_table_balance(data):
    """Property 20: For any successful transformation, all balanceChecks pass."""
    source_data, mapping, params = data
    context = _run_and_build_context(source_data, mapping, params)
    if context is None:
        return  # skip if transformation failed

    ct = generate_control_table(context)

    assert ct.totals is not None
    assert len(ct.totals.balanceChecks) > 0, "Must have at least one balance check"
    for check in ct.totals.balanceChecks:
        assert check.passed, f"Balance check failed: {check.description}"
    assert ct.generatedAt is not None


@given(data=budget_data_and_params())
@settings(max_examples=50, deadline=None)
def test_property_21_control_table_row_count_consistency(data):
    """Property 21: outputRowCount = inputRowCount × monthColumnCount."""
    source_data, mapping, params = data
    context = _run_and_build_context(source_data, mapping, params)
    if context is None:
        return

    ct = generate_control_table(context)
    num_months = len(mapping.monthColumns)

    # All rows have non-null accounts in our generated data
    expected_output = ct.totals.inputRowCount * num_months
    assert ct.totals.outputRowCount == expected_output, (
        f"Expected {expected_output} output rows "
        f"({ct.totals.inputRowCount} × {num_months}), "
        f"got {ct.totals.outputRowCount}"
    )
