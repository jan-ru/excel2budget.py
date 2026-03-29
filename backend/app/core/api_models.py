"""API request/response models for the Data Conversion Tool backend."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from backend.app.core.types import OutputTemplate


class PackageListResponse(BaseModel):
    packages: List[str]


class TemplateListResponse(BaseModel):
    templates: List[str]


class OutputTemplateResponse(BaseModel):
    template: OutputTemplate


class ErrorResponse(BaseModel):
    detail: str
    available_packages: List[str] = []
    available_templates: List[str] = []


class CreateConfigurationRequest(BaseModel):
    name: str
    packageName: str
    templateName: str
    budgetcode: str
    year: int


class UpdateConfigurationRequest(BaseModel):
    packageName: Optional[str] = None
    templateName: Optional[str] = None
    budgetcode: Optional[str] = None
    year: Optional[int] = None


class CustomerConfiguration(BaseModel):
    name: str
    packageName: str
    templateName: str
    budgetcode: str
    year: int
    createdAt: datetime
    updatedAt: datetime


class ConfigurationListResponse(BaseModel):
    configurations: List[CustomerConfiguration]
