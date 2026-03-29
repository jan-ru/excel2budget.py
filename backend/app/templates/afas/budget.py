"""Afas Budget output template definition (Pydantic)."""

from backend.app.core.types import (
    DataType,
    FixedNull,
    FromSource,
    FromUserParam,
    OutputTemplate,
    TemplateColumnDef,
)

AFAS_BUDGET = OutputTemplate(
    packageName="afas",
    templateName="budget",
    columns=[
        TemplateColumnDef(
            name="AccountCode",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Account"),
        ),
        TemplateColumnDef(
            name="BudgetCode",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromUserParam(paramName="budgetcode"),
        ),
        TemplateColumnDef(
            name="Year",
            dataType=DataType.INTEGER,
            nullable=False,
            sourceMapping=FromUserParam(paramName="year"),
        ),
        TemplateColumnDef(
            name="Period",
            dataType=DataType.INTEGER,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Amount",
            dataType=DataType.FLOAT,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Value"),
        ),
    ],
)
