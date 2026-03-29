"""Validation functions for core data structures.

Validates TabularData structural invariants, MappingConfig constraints,
and UserParams requirements.
"""

from __future__ import annotations

from typing import List

from src.core.types import MappingConfig, TabularData, UserParams, ValidationResult


def validate_tabular_data(data: TabularData) -> ValidationResult:
    """Validate TabularData structural invariants.

    Checks:
    - Every row has exactly as many values as there are columns
    - Column names are unique
    - rowCount equals the actual number of rows
    """
    errors: List[str] = []
    col_count = len(data.columns)

    # Column name uniqueness
    names = [col.name for col in data.columns]
    seen: set[str] = set()
    for name in names:
        if name in seen:
            errors.append(f"Duplicate column name: '{name}'")
        seen.add(name)

    # rowCount consistency
    actual_count = len(data.rows)
    if data.rowCount != actual_count:
        errors.append(
            f"rowCount mismatch: declared {data.rowCount}, actual {actual_count}"
        )

    # Row length matches column count
    for i, row in enumerate(data.rows):
        if len(row.values) != col_count:
            errors.append(
                f"Row {i} has {len(row.values)} values, expected {col_count}"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_mapping_config(
    config: MappingConfig, column_names: List[str]
) -> ValidationResult:
    """Validate MappingConfig constraints.

    Checks:
    - monthColumns count is between 1 and 12
    - periodNumbers are unique and in range 1–12
    - entityColumn, accountColumn, dcColumn, and all month source columns
      exist in the provided column names
    """
    errors: List[str] = []

    # Month columns count
    mc_count = len(config.monthColumns)
    if mc_count < 1 or mc_count > 12:
        errors.append(
            f"monthColumns count must be 1–12, got {mc_count}"
        )

    # Period number uniqueness and range
    period_numbers: list[int] = []
    for mc in config.monthColumns:
        if mc.periodNumber < 1 or mc.periodNumber > 12:
            errors.append(
                f"periodNumber {mc.periodNumber} for column '{mc.sourceColumnName}' "
                f"is out of range 1–12"
            )
        if mc.periodNumber in period_numbers:
            errors.append(
                f"Duplicate periodNumber {mc.periodNumber} "
                f"for column '{mc.sourceColumnName}'"
            )
        period_numbers.append(mc.periodNumber)

    # Referenced columns exist
    col_set = set(column_names)
    for ref_name, label in [
        (config.entityColumn, "entityColumn"),
        (config.accountColumn, "accountColumn"),
        (config.dcColumn, "dcColumn"),
    ]:
        if ref_name not in col_set:
            errors.append(f"{label} '{ref_name}' not found in columns")

    for mc in config.monthColumns:
        if mc.sourceColumnName not in col_set:
            errors.append(
                f"Month column '{mc.sourceColumnName}' not found in columns"
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_user_params(params: UserParams) -> ValidationResult:
    """Validate UserParams requirements.

    Checks:
    - budgetcode is a non-empty string
    - year is a positive integer
    """
    errors: List[str] = []

    if not params.budgetcode:
        errors.append("budgetcode must be non-empty")

    if params.year <= 0:
        errors.append(f"year must be positive, got {params.year}")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
