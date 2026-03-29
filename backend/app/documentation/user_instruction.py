"""User Instruction Generator for the Documentation Module.

Generates step-by-step user guidance specific to the conversion
configuration, referencing the accounting package and template.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.types import (
    ApplicationContext,
    ArtifactContentType,
    DocumentArtifact,
)


def generate_user_instruction(context: ApplicationContext) -> DocumentArtifact:
    """Generate a User Instruction document."""
    pkg = context.targetSystem.name if context.targetSystem else "Unknown"
    config_name = context.configurationName or "Unknown Configuration"

    lines = [f"# User Instruction: {config_name}", ""]
    lines.append(f"Target accounting package: {pkg}")
    lines.append("")

    if context.processSteps:
        lines.append("## Process Overview")
        lines.append("")
        for step in context.processSteps:
            lines.append(f"{step.stepNumber}. **{step.name}** ({step.actor})")
            lines.append(f"   {step.description}")
        lines.append("")

    if context.userInstructionSteps:
        lines.append("## Step-by-Step Guide")
        lines.append("")
        for i, step in enumerate(context.userInstructionSteps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    return DocumentArtifact(
        title="User Instruction",
        contentType=ArtifactContentType.USER_INSTRUCTION,
        content="\n".join(lines),
        generatedAt=datetime.now(timezone.utc),
    )
