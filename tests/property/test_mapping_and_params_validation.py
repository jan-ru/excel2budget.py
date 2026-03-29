"""Property tests for MappingConfig and UserParams validation.

**Validates: Requirements 2.2, 2.5, 4.2, 4.3**

Property 13: MappingConfig validity invariant — month columns 1–12,
unique periodNumbers, referenced columns exist in column_names.

Property 15: UserParams validation — empty budgetcode or non-positive
year rejected.
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.core.types import MappingConfig, MonthColumnDef, UserParams
from src.core.validation import validate_mapping_config, validate_user_params


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Non-empty identifier-like column names
_col_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), min_codepoint=65),
    min_size=1,
    max_size=20,
)


def _unique_names(n: int) -> st.SearchStrategy[list[str]]:
    """Generate a list of *n* unique non-empty strings."""
    return st.lists(_col_name_st, min_size=n, max_size=n, unique=True)


@st.composite
def valid_mapping_config_and_columns(draw: st.DrawFn) -> tuple[MappingConfig, list[str]]:
    """Build a MappingConfig that satisfies all constraints together with
    a column_names list that contains every referenced column."""
    num_months = draw(st.integers(min_value=1, max_value=12))

    # We need 3 fixed columns + num_months month columns — all unique
    total_cols = 3 + num_months
    all_names = draw(_unique_names(total_cols))

    entity_col = all_names[0]
    account_col = all_names[1]
    dc_col = all_names[2]
    month_col_names = all_names[3:]

    # Unique period numbers in 1..12
    period_numbers = draw(
        st.lists(
            st.integers(min_value=1, max_value=12),
            min_size=num_months,
            max_size=num_months,
            unique=True,
        )
    )

    year = draw(st.integers(min_value=2000, max_value=2100))

    month_columns = [
        MonthColumnDef(sourceColumnName=name, periodNumber=pn, year=year)
        for name, pn in zip(month_col_names, period_numbers)
    ]

    config = MappingConfig(
        entityColumn=entity_col,
        accountColumn=account_col,
        dcColumn=dc_col,
        monthColumns=month_columns,
    )

    # column_names must contain all referenced columns (may contain extras)
    extra_names = draw(
        st.lists(_col_name_st, min_size=0, max_size=5)
    )
    column_names = list(all_names) + extra_names

    return config, column_names


# ---------------------------------------------------------------------------
# Property 13a — valid MappingConfig passes validation
# ---------------------------------------------------------------------------


@given(data=valid_mapping_config_and_columns())
@settings(max_examples=200)
def test_property_13a_valid_mapping_config_passes(
    data: tuple[MappingConfig, list[str]],
):
    """A correctly constructed MappingConfig (1-12 month columns, unique
    periodNumbers in 1-12, all referenced columns exist) must pass
    validation.

    **Validates: Requirements 2.2, 2.5**
    """
    config, column_names = data
    result = validate_mapping_config(config, column_names)
    assert result.valid, f"Expected valid, got errors: {result.errors}"
    assert result.errors == []


# ---------------------------------------------------------------------------
# Property 13b — 0 or >12 month columns must fail
# ---------------------------------------------------------------------------


@given(
    data=valid_mapping_config_and_columns(),
    extra_period=st.integers(min_value=1, max_value=12),
)
@settings(max_examples=200)
def test_property_13b_zero_month_columns_fails(
    data: tuple[MappingConfig, list[str]],
    extra_period: int,
):
    """MappingConfig with 0 month columns must fail validation.

    **Validates: Requirements 2.2**
    """
    config, column_names = data
    config.monthColumns = []

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("monthColumns count" in e for e in result.errors)


@given(
    base=valid_mapping_config_and_columns(),
)
@settings(max_examples=200)
def test_property_13b_more_than_12_month_columns_fails(
    base: tuple[MappingConfig, list[str]],
):
    """MappingConfig with >12 month columns must fail validation.

    **Validates: Requirements 2.2**
    """
    config, column_names = base

    # Build 13 month columns with unique names and period numbers 1..13
    extra_names = [f"extra_month_{i}" for i in range(13)]
    config.monthColumns = [
        MonthColumnDef(sourceColumnName=name, periodNumber=i + 1, year=2025)
        for i, name in enumerate(extra_names)
    ]
    # Add the extra column names so they exist
    column_names = column_names + extra_names

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("monthColumns count" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 13c — duplicate periodNumbers must fail
# ---------------------------------------------------------------------------


@given(data=valid_mapping_config_and_columns())
@settings(max_examples=200)
def test_property_13c_duplicate_period_numbers_fails(
    data: tuple[MappingConfig, list[str]],
):
    """MappingConfig with duplicate periodNumbers must fail validation.

    **Validates: Requirements 2.2**
    """
    config, column_names = data
    assume(len(config.monthColumns) >= 2)

    # Force a duplicate by copying the first period number to the second
    config.monthColumns[1] = MonthColumnDef(
        sourceColumnName=config.monthColumns[1].sourceColumnName,
        periodNumber=config.monthColumns[0].periodNumber,
        year=config.monthColumns[1].year,
    )

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("Duplicate periodNumber" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 13d — periodNumbers outside 1-12 must fail
# ---------------------------------------------------------------------------


@given(
    data=valid_mapping_config_and_columns(),
    bad_period=st.one_of(
        st.integers(max_value=0),
        st.integers(min_value=13),
    ),
)
@settings(max_examples=200)
def test_property_13d_period_number_out_of_range_fails(
    data: tuple[MappingConfig, list[str]],
    bad_period: int,
):
    """MappingConfig with periodNumbers outside 1-12 must fail validation.

    **Validates: Requirements 2.2**
    """
    config, column_names = data
    assume(len(config.monthColumns) >= 1)

    # Replace the first month column's period number with an out-of-range value
    config.monthColumns[0] = MonthColumnDef(
        sourceColumnName=config.monthColumns[0].sourceColumnName,
        periodNumber=bad_period,
        year=config.monthColumns[0].year,
    )

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("out of range" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 13e — referencing columns not in column_names must fail
# ---------------------------------------------------------------------------


@given(data=valid_mapping_config_and_columns())
@settings(max_examples=200)
def test_property_13e_missing_entity_column_fails(
    data: tuple[MappingConfig, list[str]],
):
    """MappingConfig referencing an entityColumn not in column_names must
    fail validation.

    **Validates: Requirements 2.5**
    """
    config, column_names = data

    # Remove the entity column from column_names
    column_names = [c for c in column_names if c != config.entityColumn]

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("entityColumn" in e and "not found" in e for e in result.errors)


@given(data=valid_mapping_config_and_columns())
@settings(max_examples=200)
def test_property_13e_missing_month_source_column_fails(
    data: tuple[MappingConfig, list[str]],
):
    """MappingConfig referencing a month sourceColumnName not in
    column_names must fail validation.

    **Validates: Requirements 2.5**
    """
    config, column_names = data
    assume(len(config.monthColumns) >= 1)

    # Remove the first month column's source name from column_names
    target = config.monthColumns[0].sourceColumnName
    column_names = [c for c in column_names if c != target]

    result = validate_mapping_config(config, column_names)
    assert not result.valid
    assert any("not found" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 15a — valid UserParams passes validation
# ---------------------------------------------------------------------------


@given(
    budgetcode=st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != ""),
    year=st.integers(min_value=1, max_value=9999),
)
@settings(max_examples=200)
def test_property_15a_valid_user_params_passes(budgetcode: str, year: int):
    """A correctly constructed UserParams (non-empty budgetcode, positive
    year) must pass validation.

    **Validates: Requirements 4.2, 4.3**
    """
    params = UserParams(budgetcode=budgetcode, year=year)
    result = validate_user_params(params)
    assert result.valid, f"Expected valid, got errors: {result.errors}"
    assert result.errors == []


# ---------------------------------------------------------------------------
# Property 15b — empty budgetcode must fail
# ---------------------------------------------------------------------------


@given(year=st.integers(min_value=1, max_value=9999))
@settings(max_examples=200)
def test_property_15b_empty_budgetcode_fails(year: int):
    """UserParams with empty budgetcode must fail validation.

    **Validates: Requirements 4.2**
    """
    params = UserParams(budgetcode="", year=year)
    result = validate_user_params(params)
    assert not result.valid
    assert any("budgetcode" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 15c — non-positive year must fail
# ---------------------------------------------------------------------------


@given(year=st.integers(max_value=0))
@settings(max_examples=200)
def test_property_15c_non_positive_year_fails(year: int):
    """UserParams with non-positive year (0 or negative) must fail
    validation.

    **Validates: Requirements 4.3**
    """
    params = UserParams(budgetcode="valid", year=year)
    result = validate_user_params(params)
    assert not result.valid
    assert any("year" in e for e in result.errors)
