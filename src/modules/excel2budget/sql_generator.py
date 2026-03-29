"""SQL generation for budget data transformation.

Generates DuckDB SQL for the unpivot + DC split transformation based on
MappingConfig, OutputTemplate, and UserParams.

Requirements: 6.1, 6.2, 6.3, 6.4, 5.1, 5.3, 5.4, 5.6, 5.7, 5.8
"""

from __future__ import annotations

import re

from src.core.types import (
    FixedNull,
    FromSource,
    FromTransform,
    FromUserParam,
    MappingConfig,
    OutputTemplate,
    UserParams,
)

# Reject NUL bytes outright.
_NUL_RE = re.compile(r"\x00")


class SQLGenerationError(Exception):
    """Raised when SQL generation fails due to invalid inputs."""


def quote_identifier(name: str) -> str:
    """Quote a column/table name for safe use in DuckDB SQL.

    Escapes embedded double-quotes by doubling them and wraps the
    identifier in double-quotes.  Rejects names containing NUL bytes.

    Raises:
        SQLGenerationError: If the name contains NUL bytes or is empty.
    """
    if not name:
        raise SQLGenerationError("Identifier must be non-empty")
    if _NUL_RE.search(name):
        raise SQLGenerationError(
            f"Identifier contains NUL byte: {name!r}"
        )
    escaped = name.replace('"', '""')
    return f'"{escaped}"'


def _escape_string_literal(value: str) -> str:
    """Escape a string for use as a SQL string literal.

    Replaces single quotes with doubled single quotes.
    Rejects null bytes.
    """
    if "\x00" in value:
        raise SQLGenerationError(
            f"String literal contains null byte: {value!r}"
        )
    return value.replace("'", "''")



def generate_transform_sql(
    mapping_config: MappingConfig,
    template: OutputTemplate,
    user_params: UserParams,
) -> str:
    """Generate a DuckDB SELECT query that transforms budget data.

    The generated SQL:
    - Is SELECT-only (no DDL/DML)
    - References only the ``budget`` table
    - Uses UNPIVOT for month columns, CASE for period extraction,
      DC-based Debet/Credit split
    - Uses quoted identifiers to prevent SQL injection

    Returns:
        A syntactically valid DuckDB SQL string.

    Raises:
        SQLGenerationError: If column names contain NUL bytes or are empty.
    """
    if not mapping_config.monthColumns:
        raise SQLGenerationError("MappingConfig has no month columns")

    # Build quoted month column list for UNPIVOT
    month_cols = ", ".join(
        quote_identifier(mc.sourceColumnName)
        for mc in mapping_config.monthColumns
    )

    entity_col = quote_identifier(mapping_config.entityColumn)
    account_col = quote_identifier(mapping_config.accountColumn)
    dc_col = quote_identifier(mapping_config.dcColumn)

    # Build CASE branches mapping unpivoted column name -> period number
    case_branches = "\n".join(
        f"            WHEN '{_escape_string_literal(mc.sourceColumnName)}'"
        f" THEN {mc.periodNumber}"
        for mc in mapping_config.monthColumns
    )

    year_val = int(user_params.year)

    # Build the final SELECT column list from the template
    select_columns = _build_select_columns(template, user_params)

    sql = f"""\
WITH unpivoted AS (
    SELECT
        {entity_col} AS "Entity",
        {account_col} AS "Account",
        {dc_col} AS "DC",
        "Period_Col",
        "Value"
    FROM "budget"
    UNPIVOT ("Value" FOR "Period_Col" IN ({month_cols}))
    WHERE {account_col} IS NOT NULL
),
with_periods AS (
    SELECT
        "Entity",
        "Account",
        "DC",
        "Value",
        {year_val} AS "Jaar",
        CASE "Period_Col"
{case_branches}
        END AS "Periode"
    FROM unpivoted
)
SELECT
    {select_columns}
FROM with_periods
ORDER BY "Entity", "Account", "Periode\""""

    return sql


def _build_select_columns(
    template: OutputTemplate,
    user_params: UserParams,
) -> str:
    """Build the SELECT column expressions from the OutputTemplate.

    Maps each TemplateColumnDef to a SQL expression based on its
    sourceMapping variant.
    """
    parts: list[str] = []
    for col_def in template.columns:
        mapping = col_def.sourceMapping
        alias = quote_identifier(col_def.name)

        if isinstance(mapping, FromSource):
            # Source columns are aliased in the CTE (Entity, Account)
            src = quote_identifier(mapping.sourceColumnName)
            parts.append(f"CAST({src} AS VARCHAR) AS {alias}")

        elif isinstance(mapping, FromUserParam):
            if mapping.paramName == "budgetcode":
                lit = _escape_string_literal(user_params.budgetcode)
                parts.append(f"'{lit}' AS {alias}")
            elif mapping.paramName == "year":
                parts.append(f"{int(user_params.year)} AS {alias}")
            else:
                raise SQLGenerationError(
                    f"Unknown user param: {mapping.paramName!r}"
                )

        elif isinstance(mapping, FromTransform):
            expr = mapping.expression
            if expr == "period_number":
                parts.append(f'"Periode" AS {alias}')
            elif "DC" in expr and "ABS" in expr:
                # Credit: DC='C' -> ROUND(ABS(Value), 4)
                parts.append(
                    f'CASE WHEN "DC" = \'C\' THEN ROUND(ABS(CAST("Value" AS DOUBLE)), 4) '
                    f"ELSE NULL END AS {alias}"
                )
            elif "DC" in expr:
                # Debet: DC='D' -> ROUND(Value, 4)
                parts.append(
                    f'CASE WHEN "DC" = \'D\' THEN ROUND(CAST("Value" AS DOUBLE), 4) '
                    f"ELSE NULL END AS {alias}"
                )
            else:
                # Generic transform expression — use as-is (trusted template)
                parts.append(f"{expr} AS {alias}")

        elif isinstance(mapping, FixedNull):
            parts.append(f"NULL AS {alias}")

        else:
            raise SQLGenerationError(
                f"Unknown source mapping type: {type(mapping)}"
            )

    return ",\n    ".join(parts)
