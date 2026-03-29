"""Template registry for accounting package output templates."""

from typing import Dict, List

from src.core.types import (
    OutputTemplate,
    TabularData,
    ValidationResult,
)
from src.templates.afas.budget import AFAS_BUDGET
from src.templates.exact.budget import EXACT_BUDGET
from src.templates.twinfield.budget import TWINFIELD_BUDGET


class TemplateError(Exception):
    """Raised when a requested package/template combination does not exist."""

    def __init__(self, message: str, available_packages: List[str] | None = None,
                 available_templates: List[str] | None = None):
        super().__init__(message)
        self.available_packages = available_packages or []
        self.available_templates = available_templates or []


# Internal registry: package_name -> template_name -> OutputTemplate
_REGISTRY: Dict[str, Dict[str, OutputTemplate]] = {
    "twinfield": {"budget": TWINFIELD_BUDGET},
    "exact": {"budget": EXACT_BUDGET},
    "afas": {"budget": AFAS_BUDGET},
}


def listPackages() -> List[str]:
    """Return a list of available accounting package names."""
    return list(_REGISTRY.keys())


def listTemplates(packageName: str) -> List[str]:
    """Return a list of available template names for a given package.

    Raises TemplateError if the package does not exist.
    """
    if packageName not in _REGISTRY:
        raise TemplateError(
            f"Unknown package '{packageName}'",
            available_packages=listPackages(),
        )
    return list(_REGISTRY[packageName].keys())


def getTemplate(packageName: str, templateName: str) -> OutputTemplate:
    """Return the OutputTemplate for the given package and template name.

    Raises TemplateError if the combination does not exist.
    """
    if packageName not in _REGISTRY:
        raise TemplateError(
            f"Unknown package '{packageName}'",
            available_packages=listPackages(),
        )
    templates = _REGISTRY[packageName]
    if templateName not in templates:
        raise TemplateError(
            f"Unknown template '{templateName}' for package '{packageName}'",
            available_packages=listPackages(),
            available_templates=list(templates.keys()),
        )
    return templates[templateName]


def validateOutput(data: TabularData, template: OutputTemplate) -> ValidationResult:
    """Validate that TabularData conforms to the given OutputTemplate."""
    errors: List[str] = []

    if len(data.columns) != len(template.columns):
        errors.append(
            f"Column count mismatch: data has {len(data.columns)}, "
            f"template expects {len(template.columns)}"
        )
    else:
        for i, (dc, tc) in enumerate(zip(data.columns, template.columns)):
            if dc.name != tc.name:
                errors.append(
                    f"Column {i} name mismatch: '{dc.name}' vs expected '{tc.name}'"
                )
            if dc.dataType != tc.dataType:
                errors.append(
                    f"Column {i} type mismatch: {dc.dataType} vs expected {tc.dataType}"
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
