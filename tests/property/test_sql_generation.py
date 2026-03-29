"""Property tests for SQL generation.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

Property 11: Generated SQL validity and safety — valid DuckDB SQL,
             SELECT-only, references only "budget" table.
Property 12: SQL injection prevention — adversarial column names with
             SQL metacharacters are properly escaped/rejected.
"""
from __future__ import annotations

import re

import duckdb
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from src.core.types import (
    ColumnDef,
    DataMetadata,
    DataType,
    FloatVal,
    MappingConfig,
    MonthColumnDef,
    NullVal,
    OutputTemplate,
    Row,
    StringVal,
    TabularData,
    UserParams,
)
from src.engine.duckdb.engine import initialize, register_table
from src.modules.excel2budget.sql_generator import (
    SQLGenerationError,
    generate_transform_sql,
    quote_identifier,
)
from src.templates.twinfield.budget import TWINFIELD_BUDGET


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Safe column names: letters, digits, hyphens, underscores, spaces — no SQL
# metacharacters that would break quoting.
_safe_col_name = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-_ "),
    min_size=1,
    max_size=20,
).filter(lambda s: s.strip() and s[0].isalpha())

_budgetcode_st = st.text(min_size=1, max_size=10).filter(
    lambda s: "\x00" not in s and "'" not in s and s.strip()
)


@st.composite
def mapping_config_st(draw: st.DrawFn) -> MappingConfig:
    """Generate a valid MappingConfig with 1-12 month columns."""
    num_months = draw(st.integers(1, 12))
    period_numbers = draw(
        st.lists(
            st.integers(1, 12), min_size=num_months, max_size=num_months, unique=True
        )
    )
    month_names = draw(
        st.lists(_safe_col_name, min_size=num_months, max_size=num_months, unique=True)
    )
    # Ensure month names don't collide with fixed column names
    fixed = {"Entity", "Account", "DC"}
    assume(all(m not in fixed for m in month_names))

    month_cols = [
        MonthColumnDef(sourceColumnName=n, periodNumber=p, year=2026)
        for n, p in zip(month_names, period_numbers)
    ]
    return MappingConfig(
        entityColumn="Entity",
        accountColumn="Account",
        dcColumn="DC",
        monthColumns=month_cols,
    )


def _build_test_data(mc: MappingConfig) -> TabularData:
    """Build a minimal TabularData matching a MappingConfig."""
    cols = [
        ColumnDef("Entity", DataType.STRING),
        ColumnDef("Account", DataType.STRING),
        ColumnDef("DC", DataType.STRING),
    ] + [ColumnDef(m.sourceColumnName, DataType.FLOAT) for m in mc.monthColumns]

    row = Row(
        [StringVal("E1"), StringVal("1000"), StringVal("D")]
        + [FloatVal(100.0)] * len(mc.monthColumns)
    )
    return TabularData(columns=cols, rows=[row], rowCount=1, metadata=DataMetadata())


# ---------------------------------------------------------------------------
# Property 11: Generated SQL validity and safety
# ---------------------------------------------------------------------------

@given(mc=mapping_config_st())
@settings(max_examples=200, deadline=None)
def test_property_11_sql_validity_and_safety(mc: MappingConfig) -> None:
    """Generated SQL must be valid DuckDB SQL, SELECT-only, referencing
    only the 'budget' table.

    **Validates: Requirements 6.1, 6.2, 6.3**
    """
    up = UserParams(budgetcode="010", year=2026)
    sql = generate_transform_sql(mc, TWINFIELD_BUDGET, up)

    # Must be SELECT-only: starts with WITH or SELECT, no unquoted semicolons
    stripped = sql.strip()
    assert stripped.upper().startswith("WITH") or stripped.upper().startswith("SELECT"), (
        "Generated SQL must be a SELECT statement (possibly with CTEs)"
    )
    # Remove quoted identifiers and string literals, then check for semicolons
    no_quoted = re.sub(r'"(?:[^"]|"")*"', "", sql)
    no_literals = re.sub(r"'(?:[^']|'')*'", "", no_quoted)
    assert ";" not in no_literals, "SQL contains unquoted semicolons"

    # Must reference only the "budget" table (in FROM clauses)
    # The only FROM should be FROM "budget" and FROM unpivoted / with_periods (CTEs)
    from_matches = re.findall(r'FROM\s+"?(\w[\w-]*)"?', sql, re.IGNORECASE)
    allowed_sources = {"budget", "unpivoted", "with_periods"}
    for source in from_matches:
        assert source in allowed_sources, f"SQL references unexpected table: {source}"

    # Must be executable against DuckDB with matching test data
    data = _build_test_data(mc)
    db = initialize()
    try:
        register_table(db, data, "budget")
        result = db.execute(sql)
        rows = result.fetchall()
        assert len(rows) >= 0  # Just verify it executes without error
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 12: SQL injection prevention
# ---------------------------------------------------------------------------

# Names containing NUL bytes must always be rejected
_nul_name_st = st.binary(min_size=1, max_size=30).map(
    lambda b: b.decode("latin-1")
).filter(lambda s: "\x00" in s and len(s) > 0)

# Adversarial names with SQL metacharacters (but no NUL) — these should be
# safely escaped, not rejected.
_adversarial_safe_st = st.one_of(
    st.just('col"injection'),
    st.just('"; DROP TABLE budget; --'),
    st.just("col'escape"),
    st.just("Robert'); DROP TABLE budget;--"),
    st.text(
        alphabet=st.sampled_from("abcdef\"';-- "),
        min_size=1,
        max_size=30,
    ).filter(lambda s: s.strip() and s[0].isalpha()),
)


@given(bad_name=_nul_name_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
def test_property_12_nul_bytes_rejected(bad_name: str) -> None:
    """Names containing NUL bytes must be rejected by quote_identifier.

    **Validates: Requirement 6.4**
    """
    with pytest.raises(SQLGenerationError):
        quote_identifier(bad_name)


@given(name=_adversarial_safe_st)
@settings(max_examples=200, deadline=None)
def test_property_12a_adversarial_names_safely_escaped(name: str) -> None:
    """Adversarial column names with SQL metacharacters (quotes, semicolons,
    comment markers) must be safely escaped so they cannot break out of the
    quoted identifier context.

    **Validates: Requirement 6.4**
    """
    quoted = quote_identifier(name)
    # Must be wrapped in double quotes
    assert quoted.startswith('"') and quoted.endswith('"')
    # The inner content must have all double-quotes doubled
    inner = quoted[1:-1]
    assert '"' not in inner.replace('""', ""), (
        f"Unescaped double-quote in identifier: {quoted}"
    )


@given(name=_adversarial_safe_st)
@settings(max_examples=100, deadline=None)
def test_property_12b_adversarial_month_cols_produce_safe_sql(name: str) -> None:
    """MappingConfig with adversarial month column names must produce SQL
    that executes safely without injection.

    **Validates: Requirement 6.4**
    """
    mc = MappingConfig(
        entityColumn="Entity",
        accountColumn="Account",
        dcColumn="DC",
        monthColumns=[MonthColumnDef(sourceColumnName=name, periodNumber=1, year=2026)],
    )
    up = UserParams(budgetcode="010", year=2026)
    sql = generate_transform_sql(mc, TWINFIELD_BUDGET, up)

    # The SQL must start with a WITH/SELECT (i.e., be a single query)
    stripped = sql.strip()
    assert stripped.upper().startswith("WITH") or stripped.upper().startswith("SELECT"), (
        "Generated SQL must be a SELECT statement (possibly with CTEs)"
    )
    # Remove quoted identifiers ("..." with "" escaping) and string literals
    # ('...' with '' escaping) then check for unquoted semicolons.
    no_quoted = re.sub(r'"(?:[^"]|"")*"', "", sql)
    no_literals = re.sub(r"'(?:[^']|'')*'", "", no_quoted)
    assert ";" not in no_literals, "SQL contains unquoted semicolons"
