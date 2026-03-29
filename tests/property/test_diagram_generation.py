"""Property tests for diagram generation.

Property 25: ArchiMate diagram — contains source system, conversion tool, target
Property 26: BPMN diagram — contains all 6 process steps

Validates: Requirements 17.1.1, 17.1.2, 17.1.3, 17.2.1, 17.2.2, 17.2.3
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    ApplicationContext,
    DiagramTemplate,
    DiagramType,
    ProcessStep,
    SystemDescriptor,
)
from src.documentation.diagram_generator import (
    generate_archimate_diagram,
    generate_bpmn_diagram,
)


_safe_name = st.from_regex(r"[A-Za-z][A-Za-z0-9 ]{0,19}", fullmatch=True)


@st.composite
def archimate_context(draw: st.DrawFn):
    """Generate an ApplicationContext with source/target systems."""
    source = draw(_safe_name)
    target = draw(_safe_name)
    app = draw(_safe_name)
    num_intermediaries = draw(st.integers(min_value=0, max_value=3))
    intermediaries = [
        SystemDescriptor(
            name=draw(_safe_name),
            systemType="Tool",
            description="intermediary",
        )
        for _ in range(num_intermediaries)
    ]
    return ApplicationContext(
        applicationName=app,
        configurationName=f"{target} budget",
        sourceSystem=SystemDescriptor(name=source, systemType="Spreadsheet", description="source"),
        targetSystem=SystemDescriptor(name=target, systemType="Accounting", description="target"),
        intermediarySystems=intermediaries,
    )


@st.composite
def bpmn_context(draw: st.DrawFn):
    """Generate an ApplicationContext with 6 process steps."""
    step_names = [
        "Upload Excel File",
        "Extract Mapping",
        "Set Parameters",
        "Run Transformation",
        "Review Output",
        "Export",
    ]
    steps = [
        ProcessStep(
            stepNumber=i + 1,
            name=step_names[i],
            description=f"Step {i + 1} description",
            actor=draw(st.sampled_from(["User", "System"])),
        )
        for i in range(6)
    ]
    return ApplicationContext(
        applicationName="excel2budget",
        configurationName="test config",
        processSteps=steps,
    )


@given(ctx=archimate_context())
@settings(max_examples=50)
def test_property_25_archimate_diagram_generation(ctx):
    """Property 25: ArchiMate diagram contains source, tool, and target."""
    template = DiagramTemplate(templateType=DiagramType.ARCHIMATE)
    diagram = generate_archimate_diagram(ctx, template)

    assert diagram.diagramType == DiagramType.ARCHIMATE
    assert diagram.generatedAt is not None
    assert diagram.renderedContent, "Diagram content must not be empty"

    # Source system must appear
    assert ctx.sourceSystem.name in diagram.renderedContent, (
        f"Source system '{ctx.sourceSystem.name}' not found in diagram"
    )
    # Target system must appear
    assert ctx.targetSystem.name in diagram.renderedContent, (
        f"Target system '{ctx.targetSystem.name}' not found in diagram"
    )
    # Application name (conversion tool) must appear
    assert ctx.applicationName in diagram.renderedContent, (
        f"Application '{ctx.applicationName}' not found in diagram"
    )


@given(ctx=bpmn_context())
@settings(max_examples=50)
def test_property_26_bpmn_diagram_generation(ctx):
    """Property 26: BPMN diagram contains all 6 process steps."""
    template = DiagramTemplate(templateType=DiagramType.BPMN)
    diagram = generate_bpmn_diagram(ctx, template)

    assert diagram.diagramType == DiagramType.BPMN
    assert diagram.generatedAt is not None
    assert diagram.renderedContent, "Diagram content must not be empty"

    # All 6 process steps must appear
    for step in ctx.processSteps:
        assert step.name in diagram.renderedContent, (
            f"Process step '{step.name}' not found in BPMN diagram"
        )
