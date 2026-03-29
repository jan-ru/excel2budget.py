"""Property tests for DuckDB table registration and table name validation.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4**

Property 7:  DuckDB registration round-trip -- register TabularData,
             SELECT all, verify same schema/values/row count.
Property 19: Table name validation -- names not matching
             [a-zA-Z_][a-zA-Z0-9_]* are rejected.
"""
from __future__ import annotations

import pytest
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
from src.engine.duckdb.engine import (
    TableNameError,
    execute_sql_typed,
    initialize,
    list_tables,
    register_table,
)

_ROUNDTRIP_TYPES = [DataType.STRING, DataType.INTEGER, DataType.FLOAT, DataType.BOOLEAN]


def _cell_st(dt: DataType) -> st.SearchStrategy[CellValue]:
    """Return a strategy producing CellValues compatible with *dt*."""
    if dt == DataType.STRING:
        return st.one_of(
            st.builds(StringVal, value=st.text(max_size=50).filter(lambda s: "\x00" not in s)),
            st.just(NullVal()),
        )
    if dt == DataType.INTEGER:
        return st.one_of(
            st.builds(IntVal, value=st.integers(-10000, 10000)),
            st.just(NullVal()),
        )
    if dt == DataType.FLOAT:
        return st.one_of(
            st.builds(FloatVal, value=st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False)),
            st.just(NullVal()),
        )
    if dt == DataType.BOOLEAN:
        return st.one_of(
            st.builds(BoolVal, value=st.booleans()),
            st.just(NullVal()),
        )
    return st.just(NullVal())


# Use lowercase-only names to avoid DuckDB case-insensitive column collisions.
_col_name_st = st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True)


@st.composite
def tabular_data_st(draw: st.DrawFn) -> TabularData:
    """Build a TabularData with types that round-trip cleanly through DuckDB."""
    num_cols = draw(st.integers(1, 6))
    num_rows = draw(st.integers(0, 10))
    col_names = draw(st.lists(_col_name_st, min_size=num_cols, max_size=num_cols, unique=True))
    col_types = [draw(st.sampled_from(_ROUNDTRIP_TYPES)) for _ in range(num_cols)]
    columns = [ColumnDef(name=n, dataType=t) for n, t in zip(col_names, col_types)]
    rows = [
        Row(values=[draw(_cell_st(t)) for t in col_types])
        for _ in range(num_rows)
    ]
    return TabularData(columns=columns, rows=rows, rowCount=num_rows, metadata=DataMetadata())


def _cell_eq(a: CellValue, b: CellValue) -> bool:
    """Semantic equality for CellValues (floats use tolerance)."""
    if isinstance(a, NullVal) and isinstance(b, NullVal):
        return True
    if type(a) is not type(b):
        return False
    if isinstance(a, FloatVal) and isinstance(b, FloatVal):
        return abs(a.value - b.value) < 1e-9
    return a == b


# ---------------------------------------------------------------------------
# Property 7: DuckDB registration round-trip
# ---------------------------------------------------------------------------

@given(data=tabular_data_st())
@settings(max_examples=200, deadline=None)
def test_property_7_registration_round_trip(data: TabularData) -> None:
    """Register TabularData, SELECT all, verify same schema/values/row count.

    **Validates: Requirements 7.1, 7.2, 7.3**
    """
    db = initialize()
    try:
        register_table(db, data, "roundtrip")
        col_list = ", ".join(f'"{c.name}"' for c in data.columns)
        result = execute_sql_typed(db, f"SELECT {col_list} FROM roundtrip", data.columns)

        assert result.rowCount == data.rowCount
        assert len(result.columns) == len(data.columns)
        for orig, got in zip(data.columns, result.columns):
            assert orig.name == got.name
            assert orig.dataType == got.dataType
        for ri, (orow, grow) in enumerate(zip(data.rows, result.rows)):
            for ci, (ov, gv) in enumerate(zip(orow.values, grow.values)):
                assert _cell_eq(ov, gv), f"Mismatch row {ri} col {ci}: {ov!r} vs {gv!r}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 19: Table name validation
# ---------------------------------------------------------------------------

_invalid_name_st = st.one_of(
    st.from_regex(r"[0-9][a-zA-Z0-9_]*", fullmatch=True),
    st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]*[^a-zA-Z0-9_]+", fullmatch=True),
    st.just(""),
)


@given(bad_name=_invalid_name_st)
@settings(max_examples=200, deadline=None)
def test_property_19_invalid_table_names_rejected(bad_name: str) -> None:
    """Names not matching [a-zA-Z_][a-zA-Z0-9_]* must raise TableNameError.

    **Validates: Requirement 7.4**
    """
    db = initialize()
    try:
        dummy = TabularData(
            columns=[ColumnDef("x", DataType.INTEGER)],
            rows=[], rowCount=0, metadata=DataMetadata(),
        )
        with pytest.raises(TableNameError):
            register_table(db, dummy, bad_name)
    finally:
        db.close()


@given(good_name=st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]{0,20}", fullmatch=True))
@settings(max_examples=100, deadline=None)
def test_property_19a_valid_table_names_accepted(good_name: str) -> None:
    """Valid table names must be accepted without error.

    **Validates: Requirement 7.4**
    """
    db = initialize()
    try:
        dummy = TabularData(
            columns=[ColumnDef("x", DataType.INTEGER)],
            rows=[], rowCount=0, metadata=DataMetadata(),
        )
        register_table(db, dummy, good_name)
        assert good_name in list_tables(db)
    finally:
        db.close()
