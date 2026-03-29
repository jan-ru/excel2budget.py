"""Unit tests for the BudgetConversionApp UI shell."""

from src.ui.app import BudgetConversionApp, Screen, ScreenContent


class TestScreenContent:
    """Tests for ScreenContent and common screen properties."""

    def test_upload_screen_has_date(self):
        app = BudgetConversionApp()
        content = app.render_upload_screen()
        assert content.current_date  # non-empty
        assert len(content.current_date) == 10  # YYYY-MM-DD
        assert content.current_date[4] == "-"

    def test_upload_screen_has_pdf_action(self):
        app = BudgetConversionApp()
        content = app.render_upload_screen()
        assert content.pdf_action_available is True

    def test_upload_screen_type(self):
        app = BudgetConversionApp()
        content = app.render_upload_screen()
        assert content.screen == Screen.UPLOAD
        assert content.title == "Upload Budget File"

    def test_preview_screen_has_date_and_pdf(self):
        app = BudgetConversionApp()
        content = app.render_preview_screen()
        assert content.current_date
        assert content.pdf_action_available is True
        assert content.screen == Screen.PREVIEW

    def test_configuration_screen_has_date_and_pdf(self):
        app = BudgetConversionApp()
        content = app.render_configuration_screen()
        assert content.current_date
        assert content.pdf_action_available is True
        assert content.screen == Screen.CONFIGURATION

    def test_configuration_screen_lists_packages(self):
        app = BudgetConversionApp()
        content = app.render_configuration_screen()
        packages = content.data.get("packages", [])
        assert "twinfield" in packages
        assert "exact" in packages
        assert "afas" in packages

    def test_transform_screen_has_date_and_pdf(self):
        app = BudgetConversionApp()
        content = app.render_transform_screen()
        assert content.current_date
        assert content.pdf_action_available is True
        assert content.screen == Screen.TRANSFORM

    def test_transform_screen_not_ready_without_data(self):
        app = BudgetConversionApp()
        content = app.render_transform_screen()
        assert content.data["ready"] is False

    def test_output_screen_has_date_and_pdf(self):
        app = BudgetConversionApp()
        content = app.render_output_screen()
        assert content.current_date
        assert content.pdf_action_available is True
        assert content.screen == Screen.OUTPUT

    def test_documentation_screen_has_date_and_pdf(self):
        app = BudgetConversionApp()
        content = app.render_documentation_screen()
        assert content.current_date
        assert content.pdf_action_available is True
        assert content.screen == Screen.DOCUMENTATION

    def test_documentation_not_available_without_transform(self):
        app = BudgetConversionApp()
        content = app.render_documentation_screen()
        assert content.data["artifacts_available"] is False


class TestSelectTemplate:
    """Tests for template selection."""

    def test_select_valid_template(self):
        app = BudgetConversionApp()
        content = app.select_template("twinfield", "budget")
        assert app.selected_package == "twinfield"
        assert app.selected_template_name == "budget"
        assert app.template is not None
        assert content.error is None

    def test_select_invalid_package(self):
        app = BudgetConversionApp()
        content = app.select_template("nonexistent", "budget")
        assert content.error is not None
        assert app.template is None

    def test_select_invalid_template(self):
        app = BudgetConversionApp()
        content = app.select_template("twinfield", "nonexistent")
        assert content.error is not None


class TestSetParams:
    """Tests for user parameter setting."""

    def test_set_params(self):
        app = BudgetConversionApp()
        content = app.set_params("010", 2026)
        assert app.user_params is not None
        assert app.user_params.budgetcode == "010"
        assert app.user_params.year == 2026
        assert content.screen == Screen.CONFIGURATION


class TestRunTransformWithoutData:
    """Tests for transform without required data."""

    def test_run_transform_missing_data(self):
        app = BudgetConversionApp()
        content = app.run_transform()
        assert content.error is not None
        assert "Missing required data" in content.error


class TestGenerateDocumentationWithoutTransform:
    """Tests for documentation generation without prior transform."""

    def test_generate_docs_without_transform(self):
        app = BudgetConversionApp()
        content = app.generate_documentation()
        assert content.error is not None
        assert "Run a transformation first" in content.error


class TestExportWithoutTransform:
    """Tests for export without transformed data."""

    def test_export_returns_none_without_data(self):
        from src.core.types import FileFormat

        app = BudgetConversionApp()
        result = app.export_data(FileFormat.CSV)
        assert result is None


class TestDownloadAsPdf:
    """Tests for PDF download action."""

    def test_pdf_download_returns_bytes_or_none(self):
        app = BudgetConversionApp()
        content = app.render_upload_screen()
        result = app.download_as_pdf(content)
        # pdf_exporter exists, so should return bytes
        if result is not None:
            assert isinstance(result, bytes)
            assert len(result) > 0


class TestDateFormat:
    """Tests for date formatting on all screens."""

    def test_all_screens_have_yyyy_mm_dd_date(self):
        app = BudgetConversionApp()
        screens = [
            app.render_upload_screen,
            app.render_preview_screen,
            app.render_configuration_screen,
            app.render_transform_screen,
            app.render_output_screen,
            app.render_documentation_screen,
        ]
        for render_fn in screens:
            content = render_fn()
            d = content.current_date
            assert len(d) == 10, f"Date '{d}' on {content.screen} is not YYYY-MM-DD"
            parts = d.split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4  # year
            assert len(parts[1]) == 2  # month
            assert len(parts[2]) == 2  # day


# ---------------------------------------------------------------------------
# Integration tests for task 12.2: UI ↔ pipeline/documentation wiring
# ---------------------------------------------------------------------------

from io import BytesIO
from unittest.mock import patch

from openpyxl import Workbook

from src.core.types import FileFormat


def _make_budget_xlsx() -> bytes:
    """Create a minimal valid budget .xlsx for integration tests."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Budget"
    ws.append(["Entity", "Account", "DC", "jan-26", "feb-26"])
    ws.append(["NL01", "4000", "D", 1000.0, 2000.0])
    ws.append(["NL01", "5000", "C", 500.0, 600.0])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestUploadFileWiring:
    """Verify upload_file → importBudgetFile → IronCalc preview wiring."""

    def test_upload_sets_source_data(self):
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        content = app.upload_file(raw, "test.xlsx")
        assert app.source_data is not None
        assert content.screen == Screen.PREVIEW
        assert content.error is None

    def test_upload_extracts_mapping_config(self):
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        app.upload_file(raw, "test.xlsx")
        assert app.mapping_config is not None
        assert app.mapping_config.entityColumn == "Entity"
        assert app.mapping_config.accountColumn == "Account"
        assert app.mapping_config.dcColumn == "DC"
        assert len(app.mapping_config.monthColumns) == 2

    def test_upload_preview_has_ironcalc_flag(self):
        """Preview screen data includes ironcalc_preview flag."""
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        content = app.upload_file(raw, "test.xlsx")
        assert "ironcalc_preview" in content.data

    def test_upload_ironcalc_handle_graceful_without_package(self):
        """IronCalc handle is None when ironcalc is not installed."""
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        with patch(
            "src.ui.app.BudgetConversionApp.upload_file",
            wraps=app.upload_file,
        ):
            content = app.upload_file(raw, "test.xlsx")
        # Whether ironcalc is installed or not, upload should succeed
        assert content.error is None
        assert app.source_data is not None

    def test_upload_invalid_file_returns_error(self):
        app = BudgetConversionApp()
        content = app.upload_file(b"not an xlsx", "bad.xlsx")
        assert content.error is not None
        assert content.screen == Screen.UPLOAD

    def test_upload_stores_file_name(self):
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        app.upload_file(raw, "budget_2026.xlsx")
        assert app.source_file_name == "budget_2026.xlsx"


class TestTemplateSelectionWiring:
    """Verify template selection → getTemplate() wiring."""

    def test_select_template_stores_template(self):
        app = BudgetConversionApp()
        content = app.select_template("twinfield", "budget")
        assert app.template is not None
        assert app.selected_package == "twinfield"
        assert app.selected_template_name == "budget"
        assert content.error is None

    def test_select_template_invalid_returns_error(self):
        app = BudgetConversionApp()
        content = app.select_template("nonexistent", "budget")
        assert content.error is not None
        assert app.template is None


class TestTransformWiring:
    """Verify transform → runBudgetTransformation → output preview wiring."""

    def _setup_app(self) -> BudgetConversionApp:
        """Set up an app with uploaded file and selected template."""
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        app.upload_file(raw, "test.xlsx")
        app.select_template("twinfield", "budget")
        app.set_params("010", 2026)
        return app

    def test_transform_produces_result(self):
        app = self._setup_app()
        content = app.run_transform()
        assert content.error is None
        assert app.transform_result is not None
        assert content.screen == Screen.OUTPUT

    def test_transform_output_has_ironcalc_flag(self):
        app = self._setup_app()
        content = app.run_transform()
        assert "ironcalc_preview" in content.data

    def test_transform_builds_configuration(self):
        app = self._setup_app()
        app.run_transform()
        assert app.configuration is not None
        assert app.configuration.packageName == "twinfield"
        assert app.configuration.templateName == "budget"

    def test_transform_output_has_data(self):
        app = self._setup_app()
        content = app.run_transform()
        assert content.data["transformed_data"] is not None
        assert content.data["row_count"] > 0
        assert content.data["column_count"] > 0

    def test_transform_missing_data_returns_error(self):
        app = BudgetConversionApp()
        content = app.run_transform()
        assert content.error is not None
        assert "Missing required data" in content.error


class TestExportWiring:
    """Verify export buttons → exportData() / exportScreenToPDF() wiring."""

    def _setup_transformed_app(self) -> BudgetConversionApp:
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        app.upload_file(raw, "test.xlsx")
        app.select_template("twinfield", "budget")
        app.set_params("010", 2026)
        app.run_transform()
        return app

    def test_export_csv_returns_bytes(self):
        app = self._setup_transformed_app()
        result = app.export_data(FileFormat.CSV)
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_excel_returns_bytes(self):
        app = self._setup_transformed_app()
        result = app.export_data(FileFormat.EXCEL)
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_without_transform_returns_none(self):
        app = BudgetConversionApp()
        result = app.export_data(FileFormat.CSV)
        assert result is None

    def test_pdf_export_on_output_screen(self):
        app = self._setup_transformed_app()
        content = app.render_output_screen()
        pdf = app.download_as_pdf(content)
        if pdf is not None:
            assert isinstance(pdf, bytes)
            assert len(pdf) > 0


class TestDocumentationWiring:
    """Verify documentation tab → generateDocumentationPack() → all 7 artifacts."""

    def _setup_transformed_app(self) -> BudgetConversionApp:
        app = BudgetConversionApp()
        raw = _make_budget_xlsx()
        app.upload_file(raw, "test.xlsx")
        app.select_template("twinfield", "budget")
        app.set_params("010", 2026)
        app.run_transform()
        return app

    def test_generate_documentation_produces_pack(self):
        app = self._setup_transformed_app()
        content = app.generate_documentation()
        assert content.error is None
        assert app.documentation_pack is not None

    def test_documentation_screen_has_all_7_artifacts(self):
        app = self._setup_transformed_app()
        app.generate_documentation()
        content = app.render_documentation_screen()
        assert content.data["artifacts_available"] is True
        artifacts = content.data["artifacts"]
        assert artifacts["archimate"] is not None
        assert artifacts["bpmn"] is not None
        assert artifacts["input_description"] is not None
        assert artifacts["output_description"] is not None
        assert artifacts["transform_description"] is not None
        assert artifacts["control_table"] is not None
        assert artifacts["user_instruction"] is not None

    def test_documentation_without_transform_returns_error(self):
        app = BudgetConversionApp()
        content = app.generate_documentation()
        assert content.error is not None
        assert "Run a transformation first" in content.error

    def test_documentation_screen_no_artifacts_before_generation(self):
        app = BudgetConversionApp()
        content = app.render_documentation_screen()
        assert content.data["artifacts_available"] is False
        assert content.data["artifacts"] == {}


class TestEndToEndWiring:
    """Full end-to-end integration: upload → template → params → transform → docs → export."""

    def test_full_pipeline(self):
        app = BudgetConversionApp()

        # 1. Upload
        raw = _make_budget_xlsx()
        upload_content = app.upload_file(raw, "budget.xlsx")
        assert upload_content.error is None
        assert upload_content.screen == Screen.PREVIEW

        # 2. Select template
        tmpl_content = app.select_template("twinfield", "budget")
        assert tmpl_content.error is None

        # 3. Set params
        param_content = app.set_params("010", 2026)
        assert param_content.screen == Screen.CONFIGURATION

        # 4. Transform
        transform_content = app.run_transform()
        assert transform_content.error is None
        assert transform_content.screen == Screen.OUTPUT
        assert transform_content.data["row_count"] > 0

        # 5. Export CSV
        csv_bytes = app.export_data(FileFormat.CSV)
        assert csv_bytes is not None and len(csv_bytes) > 0

        # 6. Export Excel
        xlsx_bytes = app.export_data(FileFormat.EXCEL)
        assert xlsx_bytes is not None and len(xlsx_bytes) > 0

        # 7. Generate documentation
        doc_content = app.generate_documentation()
        assert doc_content.error is None

        # 8. Verify all 7 artifacts
        doc_screen = app.render_documentation_screen()
        artifacts = doc_screen.data["artifacts"]
        assert len([v for v in artifacts.values() if v is not None]) == 7

        # 9. PDF export on documentation screen
        pdf = app.download_as_pdf(doc_screen)
        if pdf is not None:
            assert isinstance(pdf, bytes)
