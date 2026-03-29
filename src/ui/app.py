"""Main UI application shell for the budget data conversion tool.

State-machine-based application class that manages screens, user actions,
and coordinates the pipeline, template registry, documentation module,
and PDF exporter.

Every screen includes:
- Current date display (YYYY-MM-DD)
- "Download as PDF" action

Requirements: 18.1, 18.2, 20.1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.types import (
    ApplicationContext,
    ConversionConfiguration,
    DocumentationPack,
    FileFormat,
    MappingConfig,
    OutputTemplate,
    PDFMetadata,
    ScreenCapture,
    ScreenContentType,
    TabularData,
    TransformError,
    TransformSuccess,
    UserParams,
)


# ---------------------------------------------------------------------------
# Screen enum
# ---------------------------------------------------------------------------


class Screen(Enum):
    """Application screens."""

    UPLOAD = "upload"
    PREVIEW = "preview"
    CONFIGURATION = "configuration"
    TRANSFORM = "transform"
    OUTPUT = "output"
    DOCUMENTATION = "documentation"


# ---------------------------------------------------------------------------
# Screen content dataclass
# ---------------------------------------------------------------------------


@dataclass
class ScreenContent:
    """Rendered content returned by each screen method."""

    screen: Screen
    title: str
    current_date: str
    pdf_action_available: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Application class
# ---------------------------------------------------------------------------


class BudgetConversionApp:
    """State-machine UI application for budget data conversion.

    Manages application state and provides methods for each user action.
    Each method returns a ``ScreenContent`` with the rendered screen data
    and metadata (including current date and PDF availability).
    """

    def __init__(self) -> None:
        self.current_screen: Screen = Screen.UPLOAD
        self.source_data: Optional[TabularData] = None
        self.mapping_config: Optional[MappingConfig] = None
        self.selected_package: Optional[str] = None
        self.selected_template_name: Optional[str] = None
        self.template: Optional[OutputTemplate] = None
        self.user_params: Optional[UserParams] = None
        self.transform_result: Optional[TransformSuccess] = None
        self.transform_error: Optional[str] = None
        self.exported_bytes: Optional[bytes] = None
        self.documentation_pack: Optional[DocumentationPack] = None
        self.source_file_name: str = ""
        self.configuration: Optional[ConversionConfiguration] = None
        # IronCalc handles (optional — gracefully degrade if not installed)
        self.source_workbook_handle: Any = None  # WorkbookHandle
        self.source_sheet_handle: Any = None  # SheetHandle
        self.output_sheet_handle: Any = None  # SheetHandle

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _today() -> str:
        """Return the current date formatted as YYYY-MM-DD."""
        return date.today().isoformat()

    def _base_content(self, screen: Screen, title: str) -> ScreenContent:
        """Create a ScreenContent with common fields populated."""
        return ScreenContent(
            screen=screen,
            title=title,
            current_date=self._today(),
            pdf_action_available=True,
        )

    # ------------------------------------------------------------------
    # PDF action (available on every screen)
    # ------------------------------------------------------------------

    def download_as_pdf(self, screen_content: ScreenContent) -> Optional[bytes]:
        """Generate a PDF for the given screen content.

        Delegates to ``src.export.pdf_exporter.exportScreenToPDF``.
        Returns PDF bytes on success, or ``None`` if the exporter is
        unavailable.
        """
        try:
            from src.export.pdf_exporter import exportScreenToPDF
        except (ImportError, Exception):
            return None

        capture = ScreenCapture(
            contentType=_screen_to_content_type(screen_content.screen),
            htmlContent=_render_screen_text(screen_content),
        )
        metadata = PDFMetadata(
            screenTitle=screen_content.title,
            configurationName=(
                f"{self.configuration.packageName} {self.configuration.templateName}"
                if self.configuration
                else ""
            ),
            packageName=self.selected_package or "",
            templateName=self.selected_template_name or "",
            generatedAt=datetime.now(timezone.utc),
        )
        try:
            return exportScreenToPDF(capture, metadata)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Screen 1: Upload
    # ------------------------------------------------------------------

    def render_upload_screen(self) -> ScreenContent:
        """Render the file upload screen."""
        self.current_screen = Screen.UPLOAD
        content = self._base_content(Screen.UPLOAD, "Upload Budget File")
        content.data = {
            "prompt": "Select an Excel (.xlsx) budget file to upload.",
            "accepted_formats": [".xlsx"],
        }
        return content

    def upload_file(self, raw_bytes: bytes, file_name: str = "") -> ScreenContent:
        """Handle file upload and transition to preview screen.

        Delegates to ``pipeline.import_budget_file``.
        Also loads the file into IronCalc for spreadsheet preview (Req 1.4).
        """
        from src.modules.excel2budget.pipeline import import_budget_file

        self.source_file_name = file_name
        result = import_budget_file(raw_bytes)

        if isinstance(result, str):
            # Error message returned
            content = self._base_content(Screen.UPLOAD, "Upload Budget File")
            content.error = result
            return content

        self.source_data = result

        # Try to extract mapping config
        try:
            from src.modules.excel2budget.importer import (
                extractMappingConfig,
                parseExcelFile,
            )

            wb = parseExcelFile(raw_bytes)
            if not isinstance(wb, str):
                cfg = extractMappingConfig(wb)
                if isinstance(cfg, MappingConfig):
                    self.mapping_config = cfg
        except Exception:
            pass

        # Load into IronCalc for spreadsheet preview (Req 1.4)
        try:
            from src.engine.ironcalc.engine import load_excel_file

            self.source_workbook_handle = load_excel_file(raw_bytes)
        except (ImportError, Exception):
            self.source_workbook_handle = None

        return self.render_preview_screen()

    # ------------------------------------------------------------------
    # Screen 2: Preview
    # ------------------------------------------------------------------

    def render_preview_screen(self) -> ScreenContent:
        """Render the imported data preview screen."""
        self.current_screen = Screen.PREVIEW
        content = self._base_content(Screen.PREVIEW, "Data Preview")
        content.data = {
            "source_data": self.source_data,
            "mapping_config": self.mapping_config,
            "file_name": self.source_file_name,
            "column_count": (
                len(self.source_data.columns) if self.source_data else 0
            ),
            "row_count": (
                self.source_data.rowCount if self.source_data else 0
            ),
            "ironcalc_preview": self.source_workbook_handle is not None,
        }
        return content

    # ------------------------------------------------------------------
    # Screen 3: Configuration (template selection + parameter input)
    # ------------------------------------------------------------------

    def render_configuration_screen(self) -> ScreenContent:
        """Render the template selection and parameter input screen."""
        self.current_screen = Screen.CONFIGURATION
        content = self._base_content(
            Screen.CONFIGURATION, "Configuration"
        )

        # Fetch available packages/templates
        try:
            from src.templates.registry import listPackages, listTemplates

            packages = listPackages()
            templates_by_package: Dict[str, List[str]] = {}
            for pkg in packages:
                try:
                    templates_by_package[pkg] = listTemplates(pkg)
                except Exception:
                    templates_by_package[pkg] = []
        except Exception:
            packages = []
            templates_by_package = {}

        content.data = {
            "packages": packages,
            "templates_by_package": templates_by_package,
            "selected_package": self.selected_package,
            "selected_template": self.selected_template_name,
            "user_params": self.user_params,
        }
        return content

    def select_template(
        self, package_name: str, template_name: str
    ) -> ScreenContent:
        """Select an accounting package and template."""
        from src.templates.registry import TemplateError, getTemplate

        try:
            self.template = getTemplate(package_name, template_name)
            self.selected_package = package_name
            self.selected_template_name = template_name
        except TemplateError as exc:
            content = self.render_configuration_screen()
            content.error = str(exc)
            return content

        return self.render_configuration_screen()

    def set_params(self, budgetcode: str, year: int) -> ScreenContent:
        """Set user parameters (budgetcode and year)."""
        self.user_params = UserParams(budgetcode=budgetcode, year=year)
        return self.render_configuration_screen()

    # ------------------------------------------------------------------
    # Screen 4: Transform
    # ------------------------------------------------------------------

    def render_transform_screen(self) -> ScreenContent:
        """Render the transformation trigger screen."""
        self.current_screen = Screen.TRANSFORM
        content = self._base_content(Screen.TRANSFORM, "Run Transformation")
        ready = (
            self.source_data is not None
            and self.mapping_config is not None
            and self.template is not None
            and self.user_params is not None
        )
        content.data = {
            "ready": ready,
            "transform_result": self.transform_result,
            "transform_error": self.transform_error,
        }
        return content

    def run_transform(self) -> ScreenContent:
        """Execute the budget transformation."""
        from src.modules.excel2budget.pipeline import run_budget_transformation

        if (
            self.source_data is None
            or self.mapping_config is None
            or self.template is None
            or self.user_params is None
        ):
            content = self.render_transform_screen()
            content.error = "Missing required data. Upload a file, select a template, and set parameters first."
            return content

        result = run_budget_transformation(
            self.source_data,
            self.mapping_config,
            self.template,
            self.user_params,
        )

        if isinstance(result, TransformError):
            self.transform_error = result.message
            self.transform_result = None
            content = self.render_transform_screen()
            content.error = result.message
            return content

        self.transform_result = result
        self.transform_error = None

        # Load transformed data into IronCalc for output preview (Req 8.1)
        try:
            from src.engine.ironcalc.engine import load_data

            self.output_sheet_handle = load_data(
                result.data, "Output"
            )
        except (ImportError, Exception):
            self.output_sheet_handle = None

        # Build configuration for documentation
        self.configuration = ConversionConfiguration(
            packageName=self.selected_package or "",
            templateName=self.selected_template_name or "",
            mappingConfig=self.mapping_config,
            userParams=self.user_params,
            sourceFileName=self.source_file_name,
            configurationDate=datetime.now(timezone.utc),
        )

        return self.render_output_screen()

    # ------------------------------------------------------------------
    # Screen 5: Output
    # ------------------------------------------------------------------

    def render_output_screen(self) -> ScreenContent:
        """Render the output preview screen."""
        self.current_screen = Screen.OUTPUT
        content = self._base_content(Screen.OUTPUT, "Output Preview")
        transformed = (
            self.transform_result.data if self.transform_result else None
        )
        content.data = {
            "transformed_data": transformed,
            "column_count": (
                len(transformed.columns) if transformed else 0
            ),
            "row_count": transformed.rowCount if transformed else 0,
            "export_formats": [f.value for f in FileFormat],
            "ironcalc_preview": self.output_sheet_handle is not None,
        }
        return content

    def export_data(self, file_format: FileFormat) -> Optional[bytes]:
        """Export transformed data in the requested format."""
        if self.transform_result is None:
            return None

        from src.modules.excel2budget.pipeline import export_data

        try:
            return export_data(
                self.transform_result.data, file_format, self.template
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Screen 6: Documentation
    # ------------------------------------------------------------------

    def render_documentation_screen(self) -> ScreenContent:
        """Render the documentation artifacts screen.

        Exposes all 7 individual artifacts from the DocumentationPack
        (Req 17 General criteria 1, 2).
        """
        self.current_screen = Screen.DOCUMENTATION
        content = self._base_content(Screen.DOCUMENTATION, "Documentation")

        artifacts: Dict[str, Any] = {}
        if self.documentation_pack is not None:
            pack = self.documentation_pack
            artifacts = {
                "archimate": pack.archimate,
                "bpmn": pack.bpmn,
                "input_description": pack.inputDescription,
                "output_description": pack.outputDescription,
                "transform_description": pack.transformDescription,
                "control_table": pack.controlTable,
                "user_instruction": pack.userInstruction,
            }

        content.data = {
            "documentation_pack": self.documentation_pack,
            "artifacts_available": self.documentation_pack is not None,
            "artifacts": artifacts,
        }
        return content

    def generate_documentation(self) -> ScreenContent:
        """Generate the full documentation pack."""
        if (
            self.configuration is None
            or self.source_data is None
            or self.transform_result is None
            or self.mapping_config is None
            or self.template is None
        ):
            content = self.render_documentation_screen()
            content.error = "Run a transformation first before generating documentation."
            return content

        from src.documentation.module import generate_documentation_pack
        from src.modules.excel2budget.context_builder import (
            build_application_context,
        )
        from src.modules.excel2budget.sql_generator import (
            generate_transform_sql,
        )

        try:
            sql = generate_transform_sql(
                self.mapping_config, self.template, self.user_params
            )
        except Exception:
            sql = ""

        context = build_application_context(
            self.configuration,
            self.source_data,
            self.transform_result.data,
            self.mapping_config,
            self.template,
            sql,
        )

        self.documentation_pack = generate_documentation_pack(context)
        return self.render_documentation_screen()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _screen_to_content_type(screen: Screen) -> ScreenContentType:
    """Map a Screen enum to a ScreenContentType for PDF export."""
    mapping = {
        Screen.UPLOAD: ScreenContentType.SPREADSHEET,
        Screen.PREVIEW: ScreenContentType.SPREADSHEET,
        Screen.CONFIGURATION: ScreenContentType.SPREADSHEET,
        Screen.TRANSFORM: ScreenContentType.SPREADSHEET,
        Screen.OUTPUT: ScreenContentType.SPREADSHEET,
        Screen.DOCUMENTATION: ScreenContentType.CONTROL_TABLE,
    }
    return mapping.get(screen, ScreenContentType.SPREADSHEET)


def _render_screen_text(content: ScreenContent) -> str:
    """Produce a plain-text summary of screen content for PDF body."""
    lines = [
        f"Screen: {content.title}",
        f"Date: {content.current_date}",
        "",
    ]
    if content.error:
        lines.append(f"Error: {content.error}")
        lines.append("")

    for key, value in content.data.items():
        if isinstance(value, TabularData):
            lines.append(f"{key}: [{value.rowCount} rows x {len(value.columns)} columns]")
        elif isinstance(value, DocumentationPack):
            lines.append(f"{key}: DocumentationPack (generated at {value.generatedAt})")
        else:
            lines.append(f"{key}: {value}")

    return "\n".join(lines)
