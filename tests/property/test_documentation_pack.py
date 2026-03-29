"""Property test for documentation pack completeness.

Property 27: Documentation pack completeness — pack contains all 7
non-null artifacts with dates.

Validates: Requirement 17 (General criteria)
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    ApplicationContext,
    BalanceCheck,
    ColumnDescription,
    ControlTotals,
    DataDescription,
    NamedTotal,
    ProcessStep,
    SystemDescriptor,
    TransformDescriptor,
)
from src.documentation.module import generate_documentation_pack


_safe_name = st.from_regex(r"[A-Za-z][A-Za-z0-9 ]{0,14}", fullmatch=True)


@st.composite
def full_context(draw: st.DrawFn):
    """Generate a fully populated ApplicationContext."""
    source_name = draw(_safe_name)
    target_name = draw(_safe_name)
    app_name = draw(_safe_name)

    steps = [
        ProcessStep(i + 1, f"Step{i + 1}", f"Desc {i + 1}",
                    draw(st.sampled_from(["User", "System"])))
        for i in range(6)
    ]

    src_cols = [
        ColumnDescription(name="Col1", dataType="STRING", description="c1", source="Mapping: Entity"),
    ]
    tgt_cols = [
        ColumnDescription(name="Out1", dataType="STRING", description="o1", source="Source: Col1"),
    ]

    return ApplicationContext(
        applicationName=app_name,
        configurationName=f"{target_name} budget",
        sourceSystem=SystemDescriptor(name=source_name, systemType="Spreadsheet", description="src"),
        targetSystem=SystemDescriptor(name=target_name, systemType="Accounting", description="tgt"),
        intermediarySystems=[
            SystemDescriptor(name="DuckDB", systemType="Tool", description="SQL engine"),
        ],
        processSteps=steps,
        sourceDescription=DataDescription(name="Source", columns=src_cols),
        targetDescription=DataDescription(name="Target", columns=tgt_cols),
        transformDescription=TransformDescriptor(
            name="Transform", description="test transform",
            steps=["Step A", "Step B"], generatedQuery="SELECT 1",
        ),
        controlTotals=ControlTotals(
            inputRowCount=10, outputRowCount=30,
            inputTotals=[NamedTotal(label="Values", value=1000.0)],
            outputTotals=[NamedTotal(label="Debet", value=600.0), NamedTotal(label="Credit", value=400.0)],
            balanceChecks=[BalanceCheck(description="Balance", passed=True)],
        ),
        userInstructionSteps=["Upload file", "Run transform", "Export"],
    )


@given(ctx=full_context())
@settings(max_examples=50)
def test_property_27_documentation_pack_completeness(ctx):
    """Property 27: Pack contains all 7 non-null artifacts with dates."""
    pack = generate_documentation_pack(ctx)

    # All 7 artifacts must be non-null
    assert pack.archimate is not None, "ArchiMate diagram missing"
    assert pack.bpmn is not None, "BPMN diagram missing"
    assert pack.inputDescription is not None, "Input description missing"
    assert pack.outputDescription is not None, "Output description missing"
    assert pack.transformDescription is not None, "Transform description missing"
    assert pack.controlTable is not None, "Control table missing"
    assert pack.userInstruction is not None, "User instruction missing"

    # All artifacts must have generation timestamps
    assert pack.archimate.generatedAt is not None
    assert pack.bpmn.generatedAt is not None
    assert pack.inputDescription.generatedAt is not None
    assert pack.outputDescription.generatedAt is not None
    assert pack.transformDescription.generatedAt is not None
    assert pack.controlTable.generatedAt is not None
    assert pack.userInstruction.generatedAt is not None

    # Pack itself must have a timestamp
    assert pack.generatedAt is not None

    # ApplicationContext must be preserved
    assert pack.applicationContext is ctx

    # All artifacts must have non-empty content
    assert pack.archimate.renderedContent
    assert pack.bpmn.renderedContent
    assert pack.inputDescription.content
    assert pack.outputDescription.content
    assert pack.transformDescription.content
    assert pack.userInstruction.content
