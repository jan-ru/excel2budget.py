"""Core type definitions for the Data Conversion Tool pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union


# --- Enums ---

class DataType(Enum):
    """Supported data types for column definitions."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    NULL = "NULL"


class FileFormat(Enum):
    """Supported export file formats."""
    CSV = "CSV"
    EXCEL = "EXCEL"


# --- CellValue variants ---

@dataclass(frozen=True)
class StringVal:
    value: str

@dataclass(frozen=True)
class IntVal:
    value: int

@dataclass(frozen=True)
class FloatVal:
    value: float

@dataclass(frozen=True)
class BoolVal:
    value: bool

@dataclass(frozen=True)
class DateVal:
    """Date value stored as ISO 8601 string."""
    value: str

@dataclass(frozen=True)
class NullVal:
    pass


CellValue = Union[StringVal, IntVal, FloatVal, BoolVal, DateVal, NullVal]


# --- Core data structures ---

@dataclass
class ColumnDef:
    """Definition of a single column in a tabular dataset."""
    name: str
    dataType: DataType
    nullable: bool = True


@dataclass
class Row:
    """A single row of cell values."""
    values: List[CellValue]


@dataclass
class DataMetadata:
    """Metadata attached to tabular data throughout the pipeline."""
    sourceName: str = ""
    sourceFormat: FileFormat = FileFormat.EXCEL
    importedAt: Optional[datetime] = None
    transformedAt: Optional[datetime] = None
    exportedAt: Optional[datetime] = None
    encoding: str = "utf-8"


@dataclass
class TabularData:
    """Internal representation of rows and columns with typed values."""
    columns: List[ColumnDef] = field(default_factory=list)
    rows: List[Row] = field(default_factory=list)
    rowCount: int = 0
    metadata: DataMetadata = field(default_factory=DataMetadata)


# --- Mapping types ---

@dataclass
class MonthColumnDef:
    """Maps a source column to a budget period."""
    sourceColumnName: str
    periodNumber: int  # 1..12
    year: int


@dataclass
class MappingConfig:
    """Column mapping configuration extracted from the Excel file."""
    entityColumn: str
    accountColumn: str
    dcColumn: str
    monthColumns: List[MonthColumnDef] = field(default_factory=list)


@dataclass
class UserParams:
    """User-specified parameters per conversion run."""
    budgetcode: str
    year: int


# --- ColumnSourceMapping variants ---

@dataclass(frozen=True)
class FromSource:
    """Maps from a source column."""
    sourceColumnName: str

@dataclass(frozen=True)
class FromUserParam:
    """Maps from a user-specified parameter."""
    paramName: str

@dataclass(frozen=True)
class FromTransform:
    """Computed during transformation (e.g., period extraction, DC split)."""
    expression: str

@dataclass(frozen=True)
class FixedNull:
    """Always null placeholder."""
    pass


ColumnSourceMapping = Union[FromSource, FromUserParam, FromTransform, FixedNull]


# --- Template types ---

@dataclass
class TemplateColumnDef:
    """Definition of a single column in an output template."""
    name: str
    dataType: DataType
    nullable: bool
    sourceMapping: ColumnSourceMapping


@dataclass
class OutputTemplate:
    """Target schema for a specific accounting package import format."""
    packageName: str
    templateName: str
    columns: List[TemplateColumnDef] = field(default_factory=list)


# --- Validation ---

@dataclass
class ValidationResult:
    """Result of validating output data against a template."""
    valid: bool
    errors: List[str] = field(default_factory=list)


# --- Transform result ---

@dataclass
class TransformSuccess:
    data: TabularData
    executionTimeMs: int = 0

@dataclass
class TransformError:
    message: str
    sqlState: str = ""


TransformResult = Union[TransformSuccess, TransformError]


# --- Table reference ---

@dataclass
class TableRef:
    """Reference to a registered table in the engine(s)."""
    tableName: str
    schema: List[ColumnDef] = field(default_factory=list)
    rowCount: int = 0
    registeredInDuckDB: bool = False
    registeredInIronCalc: bool = False


# --- Conversion configuration ---

@dataclass
class ConversionConfiguration:
    """Complete configuration for a single budget conversion run."""
    packageName: str
    templateName: str
    mappingConfig: MappingConfig
    userParams: UserParams
    sourceFileName: str
    configurationDate: Optional[datetime] = None


# --- Documentation Module types ---


class DiagramType(Enum):
    """Types of diagrams the documentation module can generate."""
    ARCHIMATE = "ARCHIMATE"
    BPMN = "BPMN"


class ArtifactContentType(Enum):
    """Types of document artifacts."""
    INPUT_DESCRIPTION = "INPUT_DESCRIPTION"
    OUTPUT_DESCRIPTION = "OUTPUT_DESCRIPTION"
    TRANSFORM_DESCRIPTION = "TRANSFORM_DESCRIPTION"
    USER_INSTRUCTION = "USER_INSTRUCTION"


@dataclass
class SystemDescriptor:
    """Describes a system involved in the conversion."""
    name: str
    systemType: str
    description: str


@dataclass
class ProcessStep:
    """A single step in the conversion process."""
    stepNumber: int
    name: str
    description: str
    actor: str


@dataclass
class ColumnDescription:
    """Describes a single column for documentation purposes."""
    name: str
    dataType: str
    description: str
    source: str


@dataclass
class DataDescription:
    """Describes a data structure (input or output) for documentation."""
    name: str
    columns: List[ColumnDescription] = field(default_factory=list)
    additionalNotes: str = ""


@dataclass
class TransformDescriptor:
    """Describes the transformation logic for documentation."""
    name: str
    description: str
    steps: List[str] = field(default_factory=list)
    generatedQuery: str = ""


@dataclass
class NamedTotal:
    """A labeled numeric total for control table use."""
    label: str
    value: float


@dataclass
class BalanceCheck:
    """A reconciliation check in the control table."""
    description: str
    passed: bool


@dataclass
class ControlTotals:
    """Generic control totals for reconciliation."""
    inputRowCount: int = 0
    outputRowCount: int = 0
    inputTotals: List[NamedTotal] = field(default_factory=list)
    outputTotals: List[NamedTotal] = field(default_factory=list)
    balanceChecks: List[BalanceCheck] = field(default_factory=list)


@dataclass
class ApplicationContext:
    """Generic context for the Documentation Module.

    Each application module populates this with its domain-specific
    metadata. The Documentation Module depends only on this structure.
    """
    applicationName: str = ""
    configurationName: str = ""
    configurationDate: Optional[datetime] = None

    sourceSystem: Optional[SystemDescriptor] = None
    targetSystem: Optional[SystemDescriptor] = None
    intermediarySystems: List[SystemDescriptor] = field(default_factory=list)

    processSteps: List[ProcessStep] = field(default_factory=list)

    sourceDescription: Optional[DataDescription] = None
    targetDescription: Optional[DataDescription] = None

    transformDescription: Optional[TransformDescriptor] = None

    controlTotals: Optional[ControlTotals] = None

    userInstructionSteps: List[str] = field(default_factory=list)


@dataclass
class DiagramTemplate:
    """Base template for diagram generation."""
    templateType: DiagramType
    templateContent: str = ""
    placeholders: List[str] = field(default_factory=list)


@dataclass
class DiagramOutput:
    """Generated diagram output."""
    diagramType: DiagramType
    renderedContent: str = ""
    configurationRef: str = ""
    generatedAt: Optional[datetime] = None


@dataclass
class DocumentArtifact:
    """A generated documentation artifact."""
    title: str
    contentType: ArtifactContentType
    content: str = ""
    generatedAt: Optional[datetime] = None


@dataclass
class ControlTable:
    """Generated control table with reconciliation totals."""
    totals: ControlTotals = field(default_factory=ControlTotals)
    generatedAt: Optional[datetime] = None


class ScreenContentType(Enum):
    """Types of screen content that can be captured for PDF export."""
    SPREADSHEET = "SPREADSHEET"
    DIAGRAM = "DIAGRAM"
    CONTROL_TABLE = "CONTROL_TABLE"


@dataclass
class Dimensions:
    """Width and height dimensions."""
    width: int = 800
    height: int = 600


@dataclass
class ScreenCapture:
    """Captured screen content for PDF export."""
    contentType: ScreenContentType = ScreenContentType.SPREADSHEET
    htmlContent: str = ""
    dimensions: Dimensions = field(default_factory=Dimensions)


@dataclass
class PDFMetadata:
    """Metadata included in exported PDFs."""
    screenTitle: str = ""
    configurationName: str = ""
    packageName: str = ""
    templateName: str = ""
    generatedAt: Optional[datetime] = None


@dataclass
class DocumentationPack:
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
