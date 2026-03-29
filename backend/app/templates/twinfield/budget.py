"""Twinfield Budget output template definition (Pydantic)."""

from backend.app.core.types import (
    DataType,
    FixedNull,
    FromSource,
    FromTransform,
    FromUserParam,
    OutputTemplate,
    TemplateColumnDef,
)

TWINFIELD_BUDGET = OutputTemplate(
    packageName="twinfield",
    templateName="budget",
    columns=[
        TemplateColumnDef(
            name="Entity",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Entity"),
        ),
        TemplateColumnDef(
            name="Budgetcode",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromUserParam(paramName="budgetcode"),
        ),
        TemplateColumnDef(
            name="Grootboekrekening",
            dataType=DataType.STRING,
            nullable=False,
            sourceMapping=FromSource(sourceColumnName="Account"),
        ),
        TemplateColumnDef(
            name="Kostenplaats",
            dataType=DataType.STRING,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Project",
            dataType=DataType.STRING,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Jaar",
            dataType=DataType.INTEGER,
            nullable=False,
            sourceMapping=FromUserParam(paramName="year"),
        ),
        TemplateColumnDef(
            name="Periode",
            dataType=DataType.INTEGER,
            nullable=False,
            sourceMapping=FromTransform(expression="period_number"),
        ),
        TemplateColumnDef(
            name="Debet",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FromTransform(
                expression="CASE WHEN DC='D' THEN ROUND(Value,4) ELSE NULL END"
            ),
        ),
        TemplateColumnDef(
            name="Credit",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FromTransform(
                expression="CASE WHEN DC='C' THEN ROUND(ABS(Value),4) ELSE NULL END"
            ),
        ),
        TemplateColumnDef(
            name="Hvlhd1 Debet",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Hvlhd1 Credit",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Hvlhd2 Debet",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
        TemplateColumnDef(
            name="Hvlhd2 Credit",
            dataType=DataType.FLOAT,
            nullable=True,
            sourceMapping=FixedNull(),
        ),
    ],
)
