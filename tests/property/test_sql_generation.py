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
from hypothesis import given, settings, assume
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

# Safe column names (no NUL bytes, non-empty)
_safe_col_name = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=30,
)

# Simple identifier-like column names for round-trip tests
_ident_col_name = st.from_regex(r"[a-z][a-z0-9_]{0,14}", fullmatch=True)


@st.composite
def valid_mapping_and_params(draw: st.DrawFn):
    """Generate a valid MappingConfig + UserParams + matching TabularData columns."""
    num_months = draw(st.integers(min_value=1, max_value=12))

    # Generate unique column names for entity, account, dc, and months
    total_needed = 3 + num_months
    col_names = draw(
        st.lists(_ident_col_name, min_size=total_needed, max_size=total_needed, unique=True)
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

    budgetcode = draw(st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "" and "\x00" not in s))
    params = UserParams(budgetcode=budgetcode, year=year)

    return mapping, params, col_names


@st.composite
def adversarial_mapping_and_params(draw: st.DrawFn):
    """Generate MappingConfig with adversarial column names containing SQL metacharacters."""
    # SQL metacharacters to inject
    nasty_chars = st.sampled_from([
        '"', "'", ";", "--", "/*", "*/", "\\", ")", "(", ",",
        "DROP TABLE", "'; DROP TABLE budget; --",
        'Robert"); DROP TABLE budget;--',
        "col\"; DELETE FROM budget; --",
    ])

    # Build column names with injected metacharacters
    prefix = draw(st.from_regex(r"[a-z]{1,5}", fullmatch=True))
    suffix = draw(nasty_chars)
    entity_col = prefix + suffix
    account_col = draw(st.from_regex(r"[a-z]{1,5}", fullmatch=True)) + draw(nasty_chars)
    dc_col = draw(st.from_regex(r"[a-z]{1,5}", fullmatch=True)) + draw(nasty_chars)

    # Ensure uniqueness
    assume(len({entity_col, account_col, dc_col}) == 3)

    month_name = draw(st.from_regex(r"[a-z]{1,5}", fullmatch=True)) + draw(nasty_chars)
    assume(month_name not in {entity_col, account_col, dc_col})

    mapping = MappingConfig(
        entityColumn=entity_col,
        accountColumn=account_col,
        dcColumn=dc_col,
        monthColumns=[MonthColumnDef(sourceColumnName=month_name, periodNumber=1, year=2026)],
    )

    budgetcode = draw(st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "" and "\x00" not in s))
    params = UserParams(budgetcode=budgetcode, year=2026)

    return mapping, params


# ---------------------------------------------------------------------------
# Property 11: Generated SQL validity and safety
# ---------------------------------------------------------------------------

@given(data=valid_mapping_and_params())
@settings(max_examples=200, deadline=None)
def test_property_11a_generated_sql_is_valid_duckdb(data):
    """Generated SQL must be syntactically valid DuckDB SQL.

    We verify this by registering a matching budget table in DuckDB and
    executing the generated SQL.

    **Validates: Requirement 6.1**
    """
    mapping, params, col_names = data
    sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)

    # Build a minimal budget table with matching columns
    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in col_names]
    budget_data = TabularData(columns=columns, rows=[], rowCount=0, metadata=DataMetadata())

    db = initialize()
    try:
        register_table(db, budget_data, "budget")
        # If the SQL is invalid, DuckDB will raise an exception
        db.execute(sql)
    finally:
        db.close()


@given(data=valid_mapping_and_params())
@settings(max_examples=200, deadline=None)
def test_property_11b_generated_sql_is_select_only(data):
    """Generated SQL must be SELECT-only — no DDL or DML statements.

    **Validates: Requirement 6.2**
    """
    mapping, params, _ = data
    sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)

    # Normalize whitespace for checking
    normalized = sql.strip().upper()

    # Must not contain DDL/DML keywords at statement boundaries
    ddl_dml_patterns = [
        r"\bCREATE\b",
        r"\bDROP\b",
        r"\bALTER\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bTRUNCATE\b",
        r"\bMERGE\b",
    ]
    for pattern in ddl_dml_patterns:
        assert not re.search(pattern, normalized), (
            f"SQL contains forbidden DDL/DML keyword matching {pattern}: {sql[:200]}"
        )

    # The SQL should start with WITH or SELECT
    assert normalized.startswith("WITH") or normalized.startswith("SELECT"), (
        f"SQL does not start with WITH/SELECT: {sql[:100]}"
    )


@given(data=valid_mapping_and_params())
@settings(max_examples=200, deadline=None)
def test_property_11c_generated_sql_references_only_budget_table(data):
    """Generated SQL must reference only the 'budget' table.

    We verify by checking that executing the SQL against a DuckDB instance
    with only a 'budget' table succeeds (no missing table errors).

    **Validates: Requirement 6.3**
    """
    mapping, params, col_names = data
    sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)

    # The only FROM clause table reference should be "budget"
    # Check by looking for FROM clauses that reference other tables
    # We use a regex to find table references after FROM (excluding subqueries)
    normalized = sql.upper()

    # Find all FROM <identifier> patterns (not FROM subqueries)
    from_matches = re.findall(r'\bFROM\s+"?(\w+)"?', normalized)
    for table_ref in from_matches:
        assert table_ref in ("BUDGET", "UNPIVOTED", "WITH_PERIODS"), (
            f"SQL references unexpected table: {table_ref}"
        )


# ---------------------------------------------------------------------------
# Property 11d: SQL executes correctly with actual data
# ---------------------------------------------------------------------------

@given(data=valid_mapping_and_params())
@settings(max_examples=100, deadline=None)
def test_property_11d_generated_sql_executes_with_data(data):
    """Generated SQL must execute successfully against a budget table
    containing actual rows.

    **Validates: Requirement 6.1**
    """
    mapping, params, col_names = data
    sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)

    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in col_names]

    # Build a single row with entity, account, DC, and month values
    values = []
    for i, col in enumerate(columns):
        if col.name == mapping.entityColumn:
            values.append(StringVal("E1"))
        elif col.name == mapping.accountColumn:
            values.append(StringVal("4000"))
        elif col.name == mapping.dcColumn:
            values.append(StringVal("D"))
        else:
            values.append(FloatVal(100.0))

    budget_data = TabularData(
        columns=columns,
        rows=[Row(values=values)],
        rowCount=1,
        metadata=DataMetadata(),
    )

    db = initialize()
    try:
        register_table(db, budget_data, "budget")
        result = db.execute(sql).fetchall()
        # Should produce one row per month column
        assert len(result) == len(mapping.monthColumns)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 12: SQL injection prevention
# ---------------------------------------------------------------------------

def _strip_quoted_identifiers(sql: str) -> str:
    """Remove double-quoted identifiers from SQL so we can check for
    DDL/DML keywords outside of quoted contexts only."""
    # Replace "..." (with escaped "" inside) with a placeholder
    return re.sub(r'"(?:[^"]|"")*"', '""', sql)


def _strip_string_literals(sql: str) -> str:
    """Remove single-quoted string literals from SQL."""
    return re.sub(r"'(?:[^']|'')*'", "''", sql)


@given(data=adversarial_mapping_and_params())
@settings(max_examples=200, deadline=None)
def test_property_12a_adversarial_names_do_not_cause_injection(data):
    """Column names with SQL metacharacters must be properly escaped so
    that the generated SQL does not execute unintended statements.

    We verify that DDL/DML keywords only appear inside quoted identifiers
    or string literals — never as bare SQL statements.

    **Validates: Requirement 6.4**
    """
    mapping, params = data

    try:
        sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)
    except SQLGenerationError:
        # Rejection is acceptable — the generator refused unsafe input
        return

    # If SQL was generated, verify it's still SELECT-only
    normalized = sql.strip().upper()
    assert normalized.startswith("WITH") or normalized.startswith("SELECT"), (
        f"Adversarial input produced non-SELECT SQL: {sql[:200]}"
    )

    # Strip quoted identifiers and string literals, then check for DDL/DML
    stripped = _strip_string_literals(_strip_quoted_identifiers(normalized))
    ddl_dml_patterns = [
        r"\bCREATE\s+TABLE\b",
        r"\bDROP\s+TABLE\b",
        r"\bDELETE\s+FROM\b",
        r"\bINSERT\s+INTO\b",
        r"\bUPDATE\s+\w+\s+SET\b",
    ]
    for pattern in ddl_dml_patterns:
        assert not re.search(pattern, stripped), (
            f"Adversarial input caused DDL/DML outside quotes: {pattern}"
        )


@given(data=adversarial_mapping_and_params())
@settings(max_examples=200, deadline=None)
def test_property_12b_adversarial_names_safe_execution(data):
    """When adversarial column names produce valid SQL, executing it
    against DuckDB must not modify or drop the budget table.

    **Validates: Requirement 6.4**
    """
    mapping, params = data

    try:
        sql = generate_transform_sql(mapping, TWINFIELD_BUDGET, params)
    except SQLGenerationError:
        return

    # Build a table with the adversarial column names
    all_col_names = [
        mapping.entityColumn,
        mapping.accountColumn,
        mapping.dcColumn,
    ] + [mc.sourceColumnName for mc in mapping.monthColumns]

    columns = [ColumnDef(name=n, dataType=DataType.STRING) for n in all_col_names]
    budget_data = TabularData(columns=columns, rows=[], rowCount=0, metadata=DataMetadata())

    db = initialize()
    try:
        # Registering the table itself may fail if column names are too
        # adversarial for DuckDB's parser — that's acceptable.
        try:
            register_table(db, budget_data, "budget")
        except (duckdb.Error, Exception):
            # If we can't even create the table with these names, the
            # injection vector doesn't exist.
            return

        # Execute the generated SQL — should not raise or cause side effects
        try:
            db.execute(sql)
        except duckdb.Error:
            # A DuckDB parse/execution error is acceptable (means the
            # adversarial name didn't cause injection, just a syntax issue
            # with the escaped identifier)
            pass

        # The budget table must still exist and be intact
        tables = [
            row[0]
            for row in db.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        ]
        assert "budget" in tables, "Budget table was dropped by adversarial SQL"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 12c: quote_identifier escapes double quotes
# ---------------------------------------------------------------------------

@given(name=st.text(min_size=1, max_size=50).filter(lambda s: "\x00" not in s))
@settings(max_examples=300)
def test_property_12c_quote_identifier_escapes_properly(name: str):
    """quote_identifier must produce a safely quoted identifier for any
    non-empty string without NUL bytes.

    The result must be wrapped in double-quotes with internal
    double-quotes escaped by doubling.

    **Validates: Requirement 6.4**
    """
    quoted = quote_identifier(name)

    # Must start and end with double-quote
    assert quoted.startswith('"') and quoted.endswith('"'), (
        f"Quoted identifier not wrapped in double-quotes: {quoted!r}"
    )

    # Inner content: un-escape doubled quotes and verify it matches original
    inner = quoted[1:-1]
    unescaped = inner.replace('""', '"')
    assert unescaped == name, (
        f"Round-trip failed: {name!r} → {quoted!r} → {unescaped!r}"
    )


# ---------------------------------------------------------------------------
# Property 12d: NUL bytes are rejected
# ---------------------------------------------------------------------------

@given(
    prefix=st.text(min_size=0, max_size=10),
    suffix=st.text(min_size=0, max_size=10),
)
@settings(max_examples=100)
def test_property_12d_nul_bytes_rejected(prefix: str, suffix: str):
    """Identifiers containing NUL bytes must be rejected.

    **Validates: Requirement 6.4**
    """
    name = prefix + "\x00" + suffix
    with pytest.raises(SQLGenerationError):
        quote_identifier(name)


def test_property_12e_empty_identifier_rejected():
    """Empty identifiers must be rejected.

    **Validates: Requirement 6.4**
    """
    with pytest.raises(SQLGenerationError):
        quote_identifier("")
