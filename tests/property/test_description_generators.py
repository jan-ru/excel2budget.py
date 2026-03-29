"""Property tests for description generators.

Property 28: Input description accuracy
Property 29: Output description accuracy
Property 30: Transform description accuracy

Validates: Requirements 17.3.2, 17.3.3, 17.4.2, 17.4.3, 17.5.2, 17.5.3
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    ArtifactContentType,
    ApplicationContext,
    ColumnDescription,
    DataDescription,
    TransformDescriptor,
)
from src.documentation.description_generator import (
    generate_input_description,
    generate_output_description,
    generate_transform_description,
)


_safe_name = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,14}", fullmatch=True)
_safe_type = st.sampled_from(["STRING", "INTEGER", "FLOAT", "BOOLEAN"])


@st.composite
def input_context(draw: st.DrawFn):
    """Generate an ApplicationContext with source description."""
    num_cols = draw(st.integers(min_value=1, max_value=8))
    columns = []
    for _ in range(num_cols):
        name = draw(_safe_name)
        dtype = draw(_safe_type)
        source = draw(st.sampled_from([
            "Mapping: Entity column",
            "Mapping: Account column",
            "Mapping: DC flag column",
            "Mapping: Month column (period 1)",
            "Unmapped",
        ]))
        columns.append(ColumnDescription(
            name=name, dataType=dtype,
            description=f"Source column: {name}", source=source,
        ))

    notes = draw(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
    return ApplicationContext(
        configurationName="Test Config",
        sourceDescription=DataDescription(
            name="Budget Excel File",
            columns=columns,
            additionalNotes=notes,
        ),
    )


@st.composite
def output_context(draw: st.DrawFn):
    """Generate an ApplicationContext with target description."""
    num_cols = draw(st.integers(min_value=1, max_value=8))
    columns = []
    for _ in range(num_cols):
        name = draw(_safe_name)
        dtype = draw(_safe_type)
        source = draw(st.sampled_from([
            "Source column: Entity",
            "User parameter: budgetcode",
            "Transform: period_number",
            "Fixed: null",
        ]))
        columns.append(ColumnDescription(
            name=name, dataType=dtype,
            description=f"Target column: {name}", source=source,
        ))

    notes = draw(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
    return ApplicationContext(
        configurationName="Test Config",
        targetDescription=DataDescription(
            name="Twinfield Budget Import",
            columns=columns,
            additionalNotes=notes,
        ),
    )


@st.composite
def transform_context(draw: st.DrawFn):
    """Generate an ApplicationContext with transform description."""
    steps = [
        "Filter rows with null account values",
        "UNPIVOT month columns into rows",
        "Extract period number",
        "Split Value into Debet/Credit based on DC flag",
        "Add fixed columns",
        "Reorder columns per template",
    ]
    sql = draw(st.text(min_size=10, max_size=200).filter(lambda s: s.strip()))
    return ApplicationContext(
        configurationName="Test Config",
        transformDescription=TransformDescriptor(
            name="Budget Unpivot + DC Split",
            description="Transforms wide-format to long-format",
            steps=steps,
            generatedQuery=sql,
        ),
    )


@given(ctx=input_context())
@settings(max_examples=50)
def test_property_28_input_description_accuracy(ctx):
    """Property 28: Input description lists all source columns, types, mappings."""
    doc = generate_input_description(ctx)

    assert doc.contentType == ArtifactContentType.INPUT_DESCRIPTION
    assert doc.generatedAt is not None
    assert doc.content, "Content must not be empty"

    for col in ctx.sourceDescription.columns:
        assert col.name in doc.content, f"Column '{col.name}' missing from input description"
        assert col.dataType in doc.content, f"Type '{col.dataType}' missing for column '{col.name}'"
        assert col.source in doc.content, f"Source '{col.source}' missing for column '{col.name}'"


@given(ctx=output_context())
@settings(max_examples=50)
def test_property_29_output_description_accuracy(ctx):
    """Property 29: Output description lists all target columns, types, ordering, fixed values."""
    doc = generate_output_description(ctx)

    assert doc.contentType == ArtifactContentType.OUTPUT_DESCRIPTION
    assert doc.generatedAt is not None
    assert doc.content, "Content must not be empty"

    for col in ctx.targetDescription.columns:
        assert col.name in doc.content, f"Column '{col.name}' missing from output description"
        assert col.dataType in doc.content, f"Type '{col.dataType}' missing for column '{col.name}'"
        assert col.source in doc.content, f"Source '{col.source}' missing for column '{col.name}'"


@given(ctx=transform_context())
@settings(max_examples=50)
def test_property_30_transform_description_accuracy(ctx):
    """Property 30: Transform description includes unpivot, DC split, SQL."""
    doc = generate_transform_description(ctx)

    assert doc.contentType == ArtifactContentType.TRANSFORM_DESCRIPTION
    assert doc.generatedAt is not None
    assert doc.content, "Content must not be empty"

    td = ctx.transformDescription
    # All steps must appear
    for step in td.steps:
        assert step in doc.content, f"Step '{step}' missing from transform description"

    # SQL must appear
    assert td.generatedQuery in doc.content, "Generated SQL missing from transform description"

    # Key transformation concepts must be referenced
    assert "UNPIVOT" in doc.content or "unpivot" in doc.content.lower()
    assert "DC" in doc.content or "Debet/Credit" in doc.content
