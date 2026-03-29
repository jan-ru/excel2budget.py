"""Property test for user instruction generation.

Property 31: User instruction specificity — references specific
accounting package/template, includes all process steps.

Validates: Requirements 17.7.2, 17.7.3
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    ApplicationContext,
    ArtifactContentType,
    ProcessStep,
    SystemDescriptor,
)
from src.documentation.user_instruction import generate_user_instruction


_safe_name = st.from_regex(r"[A-Za-z][A-Za-z0-9 ]{0,19}", fullmatch=True)


@st.composite
def instruction_context(draw: st.DrawFn):
    """Generate an ApplicationContext for user instruction testing."""
    pkg_name = draw(_safe_name)
    config_name = draw(_safe_name)

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
            description=f"Step {i + 1} desc",
            actor=draw(st.sampled_from(["User", "System"])),
        )
        for i in range(6)
    ]

    user_steps = [
        f"Upload your budget Excel file",
        f"Verify the column mapping",
        f"Select the target accounting package: {pkg_name}",
        f"Enter the budgetcode",
        f"Click 'Run Transformation'",
        f"Review the transformed data",
        f"Export the result",
    ]

    return ApplicationContext(
        applicationName="excel2budget",
        configurationName=config_name,
        targetSystem=SystemDescriptor(
            name=pkg_name, systemType="Accounting Package", description="target"
        ),
        processSteps=steps,
        userInstructionSteps=user_steps,
    )


@given(ctx=instruction_context())
@settings(max_examples=50)
def test_property_31_user_instruction_specificity(ctx):
    """Property 31: User instruction references package/template, includes all steps."""
    doc = generate_user_instruction(ctx)

    assert doc.contentType == ArtifactContentType.USER_INSTRUCTION
    assert doc.generatedAt is not None
    assert doc.content, "Content must not be empty"

    # Must reference the specific accounting package
    assert ctx.targetSystem.name in doc.content, (
        f"Accounting package '{ctx.targetSystem.name}' not found in user instruction"
    )

    # Must include all process steps
    for step in ctx.processSteps:
        assert step.name in doc.content, (
            f"Process step '{step.name}' not found in user instruction"
        )

    # Must include all user instruction steps
    for step_text in ctx.userInstructionSteps:
        assert step_text in doc.content, (
            f"User step '{step_text}' not found in user instruction"
        )
