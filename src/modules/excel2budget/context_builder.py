"""ApplicationContext builder for the excel2budget module.

Populates the generic ApplicationContext with excel2budget-specific
metadata so the Documentation Module can generate all 7 artifacts.

Requirements: 17 (General criteria 4)
"""

from __future__ import annotations

from src.core.types import (
    ApplicationContext,
    BalanceCheck,
    ColumnDescription,
    ControlTotals,
    ConversionConfiguration,
    DataDescription,
    FixedNull,
    FloatVal,
    FromSource,
    FromTransform,
    FromUserParam,
    IntVal,
    MappingConfig,
    NamedTotal,
    NullVal,
    OutputTemplate,
    ProcessStep,
    StringVal,
    SystemDescriptor,
    TabularData,
    TransformDescriptor,
)


def _find_column_index(data: TabularData, name: str) -> int:
    for i, col in enumerate(data.columns):
        if col.name == name:
            return i
    return -1


def _cell_to_float(cell) -> float:
    if isinstance(cell, (IntVal, FloatVal)):
        return float(cell.value)
    if isinstance(cell, StringVal):
        try:
            return float(cell.value)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _compute_control_totals(
    source_data: TabularData,
    transformed_data: TabularData,
    mapping_config: MappingConfig,
) -> ControlTotals:
    """Compute reconciliation totals for the control table.

    Input totals are computed to match the transformation output:
    - For DC="D" rows: add ROUND(value, 4) per month (preserves sign)
    - For DC="C" rows: add ROUND(ABS(value), 4) per month
    This ensures the balance check (input = Debet + Credit) holds.
    """
    acc_idx = _find_column_index(source_data, mapping_config.accountColumn)
    dc_idx = _find_column_index(source_data, mapping_config.dcColumn)
    month_indices = [
        _find_column_index(source_data, mc.sourceColumnName)
        for mc in mapping_config.monthColumns
    ]

    input_row_count = 0
    input_value_total = 0.0

    for row in source_data.rows:
        if acc_idx >= 0 and isinstance(row.values[acc_idx], NullVal):
            continue
        input_row_count += 1

        # Determine DC flag for this row
        dc_val = ""
        if dc_idx >= 0 and isinstance(row.values[dc_idx], StringVal):
            dc_val = row.values[dc_idx].value

        for mi in month_indices:
            if mi >= 0 and not isinstance(row.values[mi], NullVal):
                raw = _cell_to_float(row.values[mi])
                if dc_val == "C":
                    input_value_total += round(abs(raw), 4)
                else:
                    input_value_total += round(raw, 4)

    # Compute output totals
    debet_idx = _find_column_index(transformed_data, "Debet")
    credit_idx = _find_column_index(transformed_data, "Credit")

    output_debet_total = 0.0
    output_credit_total = 0.0

    for row in transformed_data.rows:
        if debet_idx >= 0 and not isinstance(row.values[debet_idx], NullVal):
            output_debet_total += _cell_to_float(row.values[debet_idx])
        if credit_idx >= 0 and not isinstance(row.values[credit_idx], NullVal):
            output_credit_total += _cell_to_float(row.values[credit_idx])

    balance_ok = abs(input_value_total - (output_debet_total + output_credit_total)) < 0.01

    return ControlTotals(
        inputRowCount=input_row_count,
        outputRowCount=transformed_data.rowCount,
        inputTotals=[NamedTotal(label="Budget Values", value=input_value_total)],
        outputTotals=[
            NamedTotal(label="Debet", value=output_debet_total),
            NamedTotal(label="Credit", value=output_credit_total),
        ],
        balanceChecks=[
            BalanceCheck(
                description="Sum of input values = Sum of Debet + Sum of Credit",
                passed=balance_ok,
            )
        ],
    )


def _build_source_description(
    source_data: TabularData,
    mapping_config: MappingConfig,
) -> DataDescription:
    """Build a DataDescription for the source data."""
    columns = []
    month_col_names = {mc.sourceColumnName for mc in mapping_config.monthColumns}

    for col in source_data.columns:
        if col.name == mapping_config.entityColumn:
            source = "Mapping: Entity column"
        elif col.name == mapping_config.accountColumn:
            source = "Mapping: Account column"
        elif col.name == mapping_config.dcColumn:
            source = "Mapping: DC flag column"
        elif col.name in month_col_names:
            mc = next(m for m in mapping_config.monthColumns if m.sourceColumnName == col.name)
            source = f"Mapping: Month column (period {mc.periodNumber})"
        else:
            source = "Unmapped"

        columns.append(ColumnDescription(
            name=col.name,
            dataType=col.dataType.value,
            description=f"Source column: {col.name}",
            source=source,
        ))

    return DataDescription(
        name="Budget Excel File",
        columns=columns,
        additionalNotes=f"Entity: {mapping_config.entityColumn}, "
                        f"Account: {mapping_config.accountColumn}, "
                        f"DC: {mapping_config.dcColumn}, "
                        f"Month columns: {len(mapping_config.monthColumns)}",
    )


def _build_target_description(
    template: OutputTemplate,
) -> DataDescription:
    """Build a DataDescription for the target output."""
    columns = []
    for col in template.columns:
        if isinstance(col.sourceMapping, FromSource):
            source = f"Source column: {col.sourceMapping.sourceColumnName}"
        elif isinstance(col.sourceMapping, FromUserParam):
            source = f"User parameter: {col.sourceMapping.paramName}"
        elif isinstance(col.sourceMapping, FromTransform):
            source = f"Transform: {col.sourceMapping.expression}"
        elif isinstance(col.sourceMapping, FixedNull):
            source = "Fixed: null"
        else:
            source = "Unknown"

        columns.append(ColumnDescription(
            name=col.name,
            dataType=col.dataType.value,
            description=f"Target column: {col.name}",
            source=source,
        ))

    return DataDescription(
        name=f"{template.packageName} {template.templateName} Import",
        columns=columns,
        additionalNotes=f"Package: {template.packageName}, Template: {template.templateName}",
    )


def build_application_context(
    config: ConversionConfiguration,
    source_data: TabularData,
    transformed_data: TabularData,
    mapping_config: MappingConfig,
    template: OutputTemplate,
    sql: str,
) -> ApplicationContext:
    """Build a generic ApplicationContext from excel2budget-specific data.

    This populates all fields needed by the Documentation Module to
    generate the 7 documentation artifacts.
    """
    return ApplicationContext(
        applicationName="excel2budget",
        configurationName=f"{config.packageName} {config.templateName} {config.userParams.year}",
        configurationDate=config.configurationDate,
        sourceSystem=SystemDescriptor(
            name="Excel",
            systemType="Spreadsheet",
            description=f"Budget file: {config.sourceFileName}",
        ),
        targetSystem=SystemDescriptor(
            name=config.packageName,
            systemType="Accounting Package",
            description=f"{config.templateName} import",
        ),
        intermediarySystems=[
            SystemDescriptor(
                name="IronCalc WASM",
                systemType="Conversion Tool",
                description="Spreadsheet preview",
            ),
            SystemDescriptor(
                name="DuckDB WASM",
                systemType="Conversion Tool",
                description="SQL transformation engine",
            ),
        ],
        processSteps=[
            ProcessStep(1, "Upload Excel File", "User uploads budget .xlsx file", "User"),
            ProcessStep(2, "Extract Mapping", "System reads column mapping from Excel", "System"),
            ProcessStep(3, "Set Parameters", "User specifies budgetcode and year", "User"),
            ProcessStep(4, "Run Transformation", "DuckDB executes unpivot + DC split", "System"),
            ProcessStep(5, "Review Output", "User reviews transformed data in IronCalc", "User"),
            ProcessStep(6, "Export", "User downloads result as CSV/Excel", "User"),
        ],
        sourceDescription=_build_source_description(source_data, mapping_config),
        targetDescription=_build_target_description(template),
        transformDescription=TransformDescriptor(
            name="Budget Unpivot + DC Split",
            description="Transforms wide-format budget data into long-format accounting import",
            steps=[
                "Filter rows with null account values",
                "UNPIVOT month columns into (Period, Value) rows",
                "Extract period number from month column mapping",
                "Split Value into Debet/Credit based on DC flag",
                "Add fixed columns (Budgetcode, null placeholders)",
                "Reorder columns per output template",
            ],
            generatedQuery=sql,
        ),
        controlTotals=_compute_control_totals(source_data, transformed_data, mapping_config),
        userInstructionSteps=[
            f"Upload your budget Excel file containing the Budget sheet",
            f"Verify the column mapping (Entity, Account, DC, month columns)",
            f"Select the target accounting package: {config.packageName}",
            f"Select the template: {config.templateName}",
            f"Enter the budgetcode: {config.userParams.budgetcode}",
            f"Enter the year: {config.userParams.year}",
            "Click 'Run Transformation' to execute the conversion",
            "Review the transformed data in the output preview",
            "Export the result as CSV or Excel for import into your accounting package",
        ],
    )
