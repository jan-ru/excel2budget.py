"""Property tests for TabularData structural invariants.

**Validates: Requirements 12.1, 12.2, 12.3**

Property 14: TabularData structural invariants — every Row has exactly as
many values as columns, column names are unique, and rowCount equals the
actual row count.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    BoolVal,
    CellValue,
    ColumnDef,
    DataMetadata,
    DataType,
    FloatVal,
    IntVal,
    NullVal,
    Row,
    StringVal,
    TabularData,
)
from src.core.validation import validate_tabular_data


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

cell_value_st: st.SearchStrategy[CellValue] = st.one_of(
    st.builds(StringVal, value=st.text(max_size=50)),
    st.builds(IntVal, value=st.integers(min_value=-10_000, max_value=10_000)),
    st.builds(FloatVal, value=st.floats(allow_nan=False, allow_infinity=False)),
    st.builds(BoolVal, value=st.booleans()),
    st.just(NullVal()),
)

data_type_st = st.sampled_from(list(DataType))


def _unique_column_names(n: int) -> st.SearchStrategy[list[str]]:
    """Generate a list of *n* unique non-empty column names."""
    return st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), min_codepoint=65),
            min_size=1,
            max_size=20,
        ),
        min_size=n,
        max_size=n,
        unique=True,
    )


@st.composite
def valid_tabular_data_st(draw: st.DrawFn) -> TabularData:
    """Build a TabularData instance that satisfies all structural invariants."""
    num_cols = draw(st.integers(min_value=0, max_value=8))
    num_rows = draw(st.integers(min_value=0, max_value=10))

    col_names = draw(_unique_column_names(num_cols))
    columns = [
        ColumnDef(name=name, dataType=draw(data_type_st))
        for name in col_names
    ]

    rows = [
        Row(values=draw(st.lists(cell_value_st, min_size=num_cols, max_size=num_cols)))
        for _ in range(num_rows)
    ]

    return TabularData(
        columns=columns,
        rows=rows,
        rowCount=num_rows,
        metadata=DataMetadata(),
    )


# ---------------------------------------------------------------------------
# Property 14 — valid TabularData always passes validation
# ---------------------------------------------------------------------------


@given(data=valid_tabular_data_st())
@settings(max_examples=200)
def test_property_14_valid_tabular_data_passes_validation(data: TabularData):
    """A correctly constructed TabularData must pass validation.

    Invariants checked by validate_tabular_data:
    - Every Row has exactly len(columns) values  (Req 12.1)
    - Column names are unique                    (Req 12.2)
    - rowCount == len(rows)                      (Req 12.3)
    """
    result = validate_tabular_data(data)
    assert result.valid, f"Expected valid, got errors: {result.errors}"
    assert result.errors == []


# ---------------------------------------------------------------------------
# Property 14a — row length mismatch is detected
# ---------------------------------------------------------------------------


@given(data=valid_tabular_data_st(), extra=cell_value_st)
@settings(max_examples=200)
def test_property_14a_row_length_mismatch_detected(
    data: TabularData, extra: CellValue
):
    """If any row has a different number of values than columns, validation
    must report an error (Req 12.1)."""
    if not data.rows:
        return  # need at least one existing row to corrupt

    # Append an extra value to the first row so its length != len(columns)
    data.rows[0] = Row(values=data.rows[0].values + [extra])

    result = validate_tabular_data(data)
    assert not result.valid
    assert any("values" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 14b — duplicate column names are detected
# ---------------------------------------------------------------------------


@given(base=valid_tabular_data_st())
@settings(max_examples=200)
def test_property_14b_duplicate_column_names_detected(base: TabularData):
    """If column names are not unique, validation must report an error
    (Req 12.2)."""
    if len(base.columns) < 1:
        return  # need at least one column to duplicate

    # Duplicate the first column name onto a new column
    dup_col = ColumnDef(
        name=base.columns[0].name,
        dataType=base.columns[0].dataType,
    )
    base.columns.append(dup_col)

    # Keep rows consistent with the new column count
    for row in base.rows:
        row.values.append(NullVal())

    result = validate_tabular_data(base)
    assert not result.valid
    assert any("Duplicate column name" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Property 14c — rowCount mismatch is detected
# ---------------------------------------------------------------------------


@given(data=valid_tabular_data_st())
@settings(max_examples=200)
def test_property_14c_row_count_mismatch_detected(data: TabularData):
    """If rowCount does not equal len(rows), validation must report an error
    (Req 12.3)."""
    actual = len(data.rows)
    # Set rowCount to a wrong value
    data.rowCount = actual + 1

    result = validate_tabular_data(data)
    assert not result.valid
    assert any("rowCount mismatch" in e for e in result.errors)
