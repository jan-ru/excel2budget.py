"""Exact Budget output template definition (stub)."""

from src.core.types import (
    DataType,
    FixedNull,
    FromSource,
    FromUserParam,
    OutputTemplate,
    TemplateColumnDef,
)

EXACT_BUDGET = OutputTemplate(
    packageName="exact",
    templateName="budget",
    columns=[
        TemplateColumnDef(
            name="GLAccount",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Account"),
        ),
        TemplateColumnDef(
            name="Description",
            dataType=DataType.STRING,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Amount",
            dataType=DataType.FLOAT,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Value"),
        ),
        TemplateColumnDef(
            name="BudgetScenario",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromUserParam(paramName="budgetcode"),
        ),
    ],
)
