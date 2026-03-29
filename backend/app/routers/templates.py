"""Template registry API router."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.core.api_models import (
    ErrorResponse,
    OutputTemplateResponse,
    PackageListResponse,
    TemplateListResponse,
)
from backend.app.templates.registry import (
    TemplateError,
    get_template,
    list_packages,
    list_templates,
)

router = APIRouter()


@router.get("/packages", response_model=PackageListResponse)
def get_packages() -> PackageListResponse:
    """Return the list of available accounting package names."""
    return PackageListResponse(packages=list_packages())


@router.get(
    "/packages/{package}/templates",
    response_model=TemplateListResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_templates(package: str) -> TemplateListResponse | JSONResponse:
    """Return the list of available template names for a package."""
    try:
        templates = list_templates(package)
    except TemplateError as exc:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                detail=str(exc),
                available_packages=exc.available_packages,
            ).model_dump(),
        )
    return TemplateListResponse(templates=templates)


@router.get(
    "/packages/{package}/templates/{template}",
    response_model=OutputTemplateResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_template_detail(
    package: str, template: str
) -> OutputTemplateResponse | JSONResponse:
    """Return the full OutputTemplate for a given package and template."""
    try:
        tpl = get_template(package, template)
    except TemplateError as exc:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                detail=str(exc),
                available_packages=exc.available_packages,
                available_templates=exc.available_templates,
            ).model_dump(),
        )
    return OutputTemplateResponse(template=tpl)
