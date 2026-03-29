"""Description Generator for the Documentation Module.

Generates input, output, and transform description documents
from the generic ApplicationContext.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.types import (
    ApplicationContext,
    ArtifactContentType,
    DocumentArtifact,
)


def generate_input_description(context: ApplicationContext) -> DocumentArtifact:
    """Generate an Input Description document."""
    lines = [f"# Input Description: {context.configurationName}", ""]

    src = context.sourceDescription
    if src:
        lines.append(f"## Source: {src.name}")
        lines.append("")
        if src.columns:
            lines.append("| Column | Type | Source |")
            lines.append("|--------|------|--------|")
            for col in src.columns:
                lines.append(f"| {col.name} | {col.dataType} | {col.source} |")
            lines.append("")
        if src.additionalNotes:
            lines.append(f"**Notes:** {src.additionalNotes}")
            lines.append("")

    return DocumentArtifact(
        title="Input Description",
        contentType=ArtifactContentType.INPUT_DESCRIPTION,
        content="\n".join(lines),
        generatedAt=datetime.now(timezone.utc),
    )


def generate_output_description(context: ApplicationContext) -> DocumentArtifact:
    """Generate an Output Description document."""
    lines = [f"# Output Description: {context.configurationName}", ""]

    tgt = context.targetDescription
    if tgt:
        lines.append(f"## Target: {tgt.name}")
        lines.append("")
        if tgt.columns:
            lines.append("| # | Column | Type | Source |")
            lines.append("|---|--------|------|--------|")
            for i, col in enumerate(tgt.columns, 1):
                lines.append(f"| {i} | {col.name} | {col.dataType} | {col.source} |")
            lines.append("")
        if tgt.additionalNotes:
            lines.append(f"**Notes:** {tgt.additionalNotes}")
            lines.append("")

    return DocumentArtifact(
        title="Output Description",
        contentType=ArtifactContentType.OUTPUT_DESCRIPTION,
        content="\n".join(lines),
        generatedAt=datetime.now(timezone.utc),
    )


def generate_transform_description(context: ApplicationContext) -> DocumentArtifact:
    """Generate a Transform Description document."""
    lines = [f"# Transform Description: {context.configurationName}", ""]

    td = context.transformDescription
    if td:
        lines.append(f"## {td.name}")
        lines.append("")
        lines.append(td.description)
        lines.append("")

        if td.steps:
            lines.append("### Transformation Steps")
            lines.append("")
            for i, step in enumerate(td.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        if td.generatedQuery:
            lines.append("### Generated SQL")
            lines.append("")
            lines.append("```sql")
            lines.append(td.generatedQuery)
            lines.append("```")
            lines.append("")

    return DocumentArtifact(
        title="Transform Description",
        contentType=ArtifactContentType.TRANSFORM_DESCRIPTION,
        content="\n".join(lines),
        generatedAt=datetime.now(timezone.utc),
    )
