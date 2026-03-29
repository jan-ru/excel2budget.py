"""Core Pydantic type definitions for the Data Conversion Tool backend.

Converted from dataclass-based types in src/core/types.py to Pydantic BaseModel
subclasses. These models serve as the single source of truth for the API contract;
TypeScript types are auto-generated from the OpenAPI spec produced by FastAPI.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# --- Enums ---


class DataType(str, Enum):
    """Supported data types for column definitions."""

    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    NULL = "NULL"


class FileFormat(str, Enum):
    """Supported export file formats."""

    CSV = "CSV"
    EXCEL = "EXCEL"


# --- CellValue discriminated union ---


class StringVal(BaseModel):
    type: Literal["string"] = "string"
    value: str


class IntVal(BaseModel):
    type: Literal["int"] = "int"
    value: int


class FloatVal(BaseModel):
    type: Literal["float"] = "float"
    value: float


class BoolVal(BaseModel):
    type: Literal["bool"] = "bool"
    value: bool


class DateVal(BaseModel):
    """Date value stored as ISO 8601 string."""

    type: Literal["date"] = "date"
    value: str


class NullVal(BaseModel):
    type: Literal["null"] = "null"


CellValue = Annotated[
    Union[StringVal, IntVal, FloatVal, BoolVal, DateVal, NullVal],
    Field(discriminator="type"),
]


# --- Core data structures ---


class ColumnDef(BaseModel):
    """Definition of a single column in a tabular dataset."""

    name: str
    dataType: DataType
    nullable: bool = True


class Row(BaseModel):
    """A single row of cell values."""

    values: List[CellValue]


class DataMetadata(BaseModel):
    """Metadata attached to tabular data throughout the pipeline."""

    sourceName: str = ""
    sourceFormat: FileFormat = FileFormat.EXCEL
    importedAt: Optional[datetime] = None
    transformedAt: Optional[datetime] = None
    exportedAt: Optional[datetime] = None
    encoding: str = "utf-8"


class TabularData(BaseModel):
    """Internal representation of rows and columns with typed values."""

    columns: List[ColumnDef] = []
    rows: List[Row] = []
    rowCount: int = 0
    metadata: DataMetadata = DataMetadata()


# --- Mapping types ---


class MonthColumnDef(BaseModel):
    """Maps a source column to a budget period."""

    sourceColumnName: str
    periodNumber: int  # 1..12
    year: int


class MappingConfig(BaseModel):
    """Column mapping configuration extracted from the Excel file."""

    entityColumn: str
    accountColumn: str
    dcColumn: str
    monthColumns: List[MonthColumnDef] = []


class UserParams(BaseModel):
    """User-specified parameters per conversion run."""

    budgetcode: str
    year: int


# --- ColumnSourceMapping discriminated union ---


class FromSource(BaseModel):
    """Maps from a source column."""

    type: Literal["from_source"] = "from_source"
    sourceColumnName: str


class FromUserParam(BaseModel):
    """Maps from a user-specified parameter."""

    type: Literal["from_user_param"] = "from_user_param"
    paramName: str


class FromTransform(BaseModel):
    """Computed during transformation (e.g., period extraction, DC split)."""

    type: Literal["from_transform"] = "from_transform"
    expression: str


class FixedNull(BaseModel):
    """Always null placeholder."""

    type: Literal["fixed_null"] = "fixed_null"


ColumnSourceMapping = Annotated[
    Union[FromSource, FromUserParam, FromTransform, FixedNull],
    Field(discriminator="type"),
]


# --- Template types ---


class TemplateColumnDef(BaseModel):
    """Definition of a single column in an output template."""

    name: str
    dataType: DataType
    nullable: bool
    sourceMapping: ColumnSourceMapping


class OutputTemplate(BaseModel):
    """Target schema for a specific accounting package import format."""

    packageName: str
    templateName: str
    columns: List[TemplateColumnDef] = []


# --- Validation ---


class ValidationResult(BaseModel):
    """Result of validating output data against a template."""

    valid: bool
    errors: List[str] = []


# --- Documentation Module types ---


class DiagramType(str, Enum):
    """Types of diagrams the documentation module can generate."""

    ARCHIMATE = "ARCHIMATE"
    BPMN = "BPMN"


class ArtifactContentType(str, Enum):
    """Types of document artifacts."""

    INPUT_DESCRIPTION = "INPUT_DESCRIPTION"
    OUTPUT_DESCRIPTION = "OUTPUT_DESCRIPTION"
    TRANSFORM_DESCRIPTION = "TRANSFORM_DESCRIPTION"
    USER_INSTRUCTION = "USER_INSTRUCTION"


class SystemDescriptor(BaseModel):
    """Describes a system involved in the conversion."""

    name: str
    systemType: str
    description: str


class ProcessStep(BaseModel):
    """A single step in the conversion process."""

    stepNumber: int
    name: str
    description: str
    actor: str


class ColumnDescription(BaseModel):
    """Describes a single column for documentation purposes."""

    name: str
    dataType: str
    description: str
    source: str


class DataDescription(BaseModel):
    """Describes a data structure (input or output) for documentation."""

    name: str
    columns: List[ColumnDescription] = []
    additionalNotes: str = ""


class TransformDescriptor(BaseModel):
    """Describes the transformation logic for documentation."""

    name: str
    description: str
    steps: List[str] = []
    generatedQuery: str = ""


class NamedTotal(BaseModel):
    """A labeled numeric total for control table use."""

    label: str
    value: float


class BalanceCheck(BaseModel):
    """A reconciliation check in the control table."""

    description: str
    passed: bool


class ControlTotals(BaseModel):
    """Generic control totals for reconciliation."""

    inputRowCount: int = 0
    outputRowCount: int = 0
    inputTotals: List[NamedTotal] = []
    outputTotals: List[NamedTotal] = []
    balanceChecks: List[BalanceCheck] = []


class ApplicationContext(BaseModel):
    """Generic context for the Documentation Module.

    Each application module populates this with its domain-specific
    metadata. The Documentation Module depends only on this structure.
    """

    applicationName: str = ""
    configurationName: str = ""
    configurationDate: Optional[datetime] = None
    sourceSystem: Optional[SystemDescriptor] = None
    targetSystem: Optional[SystemDescriptor] = None
    intermediarySystems: List[SystemDescriptor] = []
    processSteps: List[ProcessStep] = []
    sourceDescription: Optional[DataDescription] = None
    targetDescription: Optional[DataDescription] = None
    transformDescription: Optional[TransformDescriptor] = None
    controlTotals: Optional[ControlTotals] = None
    userInstructionSteps: List[str] = []


class DiagramTemplate(BaseModel):
    """Base template for diagram generation."""

    templateType: DiagramType
    templateContent: str = ""
    placeholders: List[str] = []


class DiagramOutput(BaseModel):
    """Generated diagram output."""

    diagramType: DiagramType
    renderedContent: str = ""
    configurationRef: str = ""
    generatedAt: Optional[datetime] = None


class DocumentArtifact(BaseModel):
    """A generated documentation artifact."""

    title: str
    contentType: ArtifactContentType
    content: str = ""
    generatedAt: Optional[datetime] = None


class ControlTable(BaseModel):
    """Generated control table with reconciliation totals."""

    totals: ControlTotals = ControlTotals()
    generatedAt: Optional[datetime] = None


class ScreenContentType(str, Enum):
    """Types of screen content that can be captured for PDF export."""

    SPREADSHEET = "SPREADSHEET"
    DIAGRAM = "DIAGRAM"
    CONTROL_TABLE = "CONTROL_TABLE"


class PDFMetadata(BaseModel):
    """Metadata included in exported PDFs."""

    screenTitle: str = ""
    configurationName: str = ""
    packageName: str = ""
    templateName: str = ""
    generatedAt: Optional[datetime] = None


class DocumentationPack(BaseModel):
    """Complete set of 7 documentation artifacts."""

    archimate: Optional[DiagramOutput] = None
    bpmn: Optional[DiagramOutput] = None
    inputDescription: Optional[DocumentArtifact] = None
    outputDescription: Optional[DocumentArtifact] = None
    transformDescription: Optional[DocumentArtifact] = None
    controlTable: Optional[ControlTable] = None
    userInstruction: Optional[DocumentArtifact] = None
    applicationContext: Optional[ApplicationContext] = None
    generatedAt: Optional[datetime] = None
