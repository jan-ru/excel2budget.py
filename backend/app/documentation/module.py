"""Documentation Module orchestrator.

Wires together diagram generator, control table generator,
description generator, and user instruction generator to produce
a complete DocumentationPack with all 7 artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.core.types import (
    ApplicationContext,
    DiagramTemplate,
    DiagramType,
    DocumentationPack,
)
from backend.app.documentation.control_table import generate_control_table
from backend.app.documentation.description_generator import (
    generate_input_description,
    generate_output_description,
    generate_transform_description,
)
from backend.app.documentation.diagram_generator import (
    generate_archimate_diagram,
    generate_bpmn_diagram,
)
from backend.app.documentation.user_instruction import generate_user_instruction


def generate_documentation_pack(
    context: ApplicationContext,
    archimate_template: DiagramTemplate | None = None,
    bpmn_template: DiagramTemplate | None = None,
) -> DocumentationPack:
    """Generate a complete DocumentationPack with all 7 artifacts."""
    if archimate_template is None:
        archimate_template = DiagramTemplate(templateType=DiagramType.ARCHIMATE)
    if bpmn_template is None:
        bpmn_template = DiagramTemplate(templateType=DiagramType.BPMN)

    now = datetime.now(timezone.utc)

    archimate = generate_archimate_diagram(context, archimate_template)
    bpmn = generate_bpmn_diagram(context, bpmn_template)
    input_desc = generate_input_description(context)
    output_desc = generate_output_description(context)
    transform_desc = generate_transform_description(context)
    control_table = generate_control_table(context)
    user_instruction = generate_user_instruction(context)

    return DocumentationPack(
        archimate=archimate,
        bpmn=bpmn,
        inputDescription=input_desc,
        outputDescription=output_desc,
        transformDescription=transform_desc,
        controlTable=control_table,
        userInstruction=user_instruction,
        applicationContext=context,
        generatedAt=now,
    )
