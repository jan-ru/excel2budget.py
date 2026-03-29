"""Template registry for accounting package output templates (Pydantic)."""

from __future__ import annotations

from typing import Dict, List

from backend.app.core.types import OutputTemplate
from backend.app.templates.afas.budget import AFAS_BUDGET
from backend.app.templates.exact.budget import EXACT_BUDGET
from backend.app.templates.twinfield.budget import TWINFIELD_BUDGET


class TemplateError(Exception):
    """Raised when a requested package/template combination does not exist."""

    def __init__(
        self,
        message: str,
        available_packages: List[str] | None = None,
        available_templates: List[str] | None = None,
    ):
        super().__init__(message)
        self.available_packages = available_packages or []
        self.available_templates = available_templates or []


# Internal registry: package_name -> template_name -> OutputTemplate
_REGISTRY: Dict[str, Dict[str, OutputTemplate]] = {
    "twinfield": {"budget": TWINFIELD_BUDGET},
    "exact": {"budget": EXACT_BUDGET},
    "afas": {"budget": AFAS_BUDGET},
}


def list_packages() -> List[str]:
    """Return available accounting package names."""
    return list(_REGISTRY.keys())


def list_templates(package_name: str) -> List[str]:
    """Return available template names for a package.

    Raises TemplateError if the package does not exist.
    """
    if package_name not in _REGISTRY:
        raise TemplateError(
            f"Unknown package '{package_name}'",
            available_packages=list_packages(),
        )
    return list(_REGISTRY[package_name].keys())


def get_template(package_name: str, template_name: str) -> OutputTemplate:
    """Return the OutputTemplate for the given package and template.

    Raises TemplateError if the combination does not exist.
    """
    if package_name not in _REGISTRY:
        raise TemplateError(
            f"Unknown package '{package_name}'",
            available_packages=list_packages(),
        )
    templates = _REGISTRY[package_name]
    if template_name not in templates:
        raise TemplateError(
            f"Unknown template '{template_name}' for package '{package_name}'",
            available_packages=list_packages(),
            available_templates=list(templates.keys()),
        )
    return templates[template_name]
