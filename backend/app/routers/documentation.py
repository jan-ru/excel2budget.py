"""Documentation generation API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.core.types import ApplicationContext, DocumentationPack
from backend.app.documentation.module import generate_documentation_pack

router = APIRouter()


def _validate_context(context: ApplicationContext) -> list[str]:
    """Return a list of missing required fields for documentation generation."""
    errors: list[str] = []
    if not context.sourceSystem:
        errors.append("sourceSystem is required")
    if not context.targetSystem:
        errors.append("targetSystem is required")
    if not context.processSteps:
        errors.append("processSteps must not be empty")
    if not context.sourceDescription:
        errors.append("sourceDescription is required")
    if not context.targetDescription:
        errors.append("targetDescription is required")
    if not context.transformDescription:
        errors.append("transformDescription is required")
    if context.controlTotals is None:
        errors.append("controlTotals is required")
    if not context.userInstructionSteps:
        errors.append("userInstructionSteps must not be empty")
    return errors


@router.post("/generate", response_model=DocumentationPack)
def generate_documentation(context: ApplicationContext) -> DocumentationPack:
    """Generate all 7 documentation artifacts from an ApplicationContext."""
    errors = _validate_context(context)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incomplete ApplicationContext: {'; '.join(errors)}",
        )
    return generate_documentation_pack(context)
