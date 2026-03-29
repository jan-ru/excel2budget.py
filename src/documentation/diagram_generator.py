"""Diagram Generator for the Documentation Module.

Generates ArchiMate and BPMN diagrams from standard templates,
populated with context-specific values.

Requirements: 17.1.1, 17.1.2, 17.1.3, 17.2.1, 17.2.2, 17.2.3
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.types import (
    ApplicationContext,
    DiagramOutput,
    DiagramTemplate,
    DiagramType,
)


def generate_archimate_diagram(
    context: ApplicationContext,
    archimate_template: DiagramTemplate,
) -> DiagramOutput:
    """Generate an ArchiMate application-layer diagram.

    Populates the template with source system, conversion tool,
    and target accounting package from the ApplicationContext.
    """
    source_name = context.sourceSystem.name if context.sourceSystem else "Unknown"
    target_name = context.targetSystem.name if context.targetSystem else "Unknown"
    app_name = context.applicationName or "Conversion Tool"

    intermediaries = ", ".join(
        s.name for s in context.intermediarySystems
    ) if context.intermediarySystems else ""

    # Start with template content or generate default
    content = archimate_template.templateContent if archimate_template.templateContent else ""

    # Replace placeholders
    replacements = {
        "{{SOURCE_SYSTEM}}": source_name,
        "{{TARGET_SYSTEM}}": target_name,
        "{{APPLICATION_NAME}}": app_name,
        "{{INTERMEDIARY_SYSTEMS}}": intermediaries,
        "{{CONFIGURATION_NAME}}": context.configurationName or "",
    }

    if content:
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
    else:
        # Generate a simple SVG diagram
        content = _generate_archimate_svg(
            source_name, app_name, target_name,
            context.intermediarySystems or [],
        )

    return DiagramOutput(
        diagramType=DiagramType.ARCHIMATE,
        renderedContent=content,
        configurationRef=context.configurationName or "",
        generatedAt=datetime.now(timezone.utc),
    )


def _generate_archimate_svg(source, app, target, intermediaries):
    """Generate a simple SVG ArchiMate diagram."""
    systems = [source, app] + [s.name for s in intermediaries] + [target]
    boxes = []
    x = 20
    for name in systems:
        boxes.append(
            f'<rect x="{x}" y="40" width="120" height="60" '
            f'fill="#e8f0fe" stroke="#4285f4" rx="5"/>'
            f'<text x="{x + 60}" y="75" text-anchor="middle" '
            f'font-size="12">{name}</text>'
        )
        x += 150

    width = x + 20
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="140">'
        + "".join(boxes)
        + "</svg>"
    )
    return svg


def generate_bpmn_diagram(
    context: ApplicationContext,
    bpmn_template: DiagramTemplate,
) -> DiagramOutput:
    """Generate a BPMN process flow diagram.

    Populates the template with process steps from the ApplicationContext.
    """
    content = bpmn_template.templateContent if bpmn_template.templateContent else ""

    if content and context.processSteps:
        for step in context.processSteps:
            placeholder = f"{{{{STEP_{step.stepNumber}_NAME}}}}"
            content = content.replace(placeholder, step.name)
            placeholder_desc = f"{{{{STEP_{step.stepNumber}_DESC}}}}"
            content = content.replace(placeholder_desc, step.description)
    else:
        content = _generate_bpmn_svg(context.processSteps or [])

    return DiagramOutput(
        diagramType=DiagramType.BPMN,
        renderedContent=content,
        configurationRef=context.configurationName or "",
        generatedAt=datetime.now(timezone.utc),
    )


def _generate_bpmn_svg(steps):
    """Generate a simple SVG BPMN diagram."""
    elements = []
    x = 20

    # Start event
    elements.append(
        f'<circle cx="{x + 15}" cy="70" r="15" '
        f'fill="#c8e6c9" stroke="#388e3c"/>'
    )
    x += 50

    for step in steps:
        elements.append(
            f'<rect x="{x}" y="40" width="140" height="60" '
            f'fill="#fff3e0" stroke="#f57c00" rx="5"/>'
            f'<text x="{x + 70}" y="65" text-anchor="middle" '
            f'font-size="11">{step.name}</text>'
            f'<text x="{x + 70}" y="85" text-anchor="middle" '
            f'font-size="9" fill="#666">{step.actor}</text>'
        )
        x += 170

    # End event
    elements.append(
        f'<circle cx="{x + 15}" cy="70" r="15" '
        f'fill="#ffcdd2" stroke="#d32f2f" stroke-width="3"/>'
    )
    x += 50

    width = x + 20
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="140">'
        + "".join(elements)
        + "</svg>"
    )
    return svg
