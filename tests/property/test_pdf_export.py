"""Property tests for PDF export.

**Property 24: PDF export availability** — produces non-empty valid PDF
with screen content and date stamp.

**Validates: Requirements 20.1, 20.2, 20.3, 20.4**
"""

from __future__ import annotations

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.types import (
    Dimensions,
    PDFMetadata,
    ScreenCapture,
    ScreenContentType,
)
from src.export.pdf_exporter import exportScreenToPDF


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x00",
    ),
    min_size=0,
    max_size=200,
)

_screen_content_type = st.sampled_from(list(ScreenContentType))

_nonempty_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
    ),
    min_size=1,
    max_size=30,
)


@st.composite
def screen_capture_and_metadata(draw: st.DrawFn):
    """Generate a ScreenCapture and PDFMetadata pair."""
    content_type = draw(_screen_content_type)
    html_content = draw(_safe_text)
    width = draw(st.integers(min_value=100, max_value=2000))
    height = draw(st.integers(min_value=100, max_value=2000))

    screen = ScreenCapture(
        contentType=content_type,
        htmlContent=html_content,
        dimensions=Dimensions(width=width, height=height),
    )

    title = draw(_nonempty_text)
    config_name = draw(_nonempty_text)
    package_name = draw(_nonempty_text)
    template_name = draw(_nonempty_text)
    generated_at = datetime.now(timezone.utc)

    metadata = PDFMetadata(
        screenTitle=title,
        configurationName=config_name,
        packageName=package_name,
        templateName=template_name,
        generatedAt=generated_at,
    )

    return screen, metadata


# ---------------------------------------------------------------------------
# Property 24: PDF export availability
# ---------------------------------------------------------------------------


@given(data=screen_capture_and_metadata())
@settings(max_examples=50, deadline=None)
def test_property_24_pdf_export_produces_nonempty_valid_pdf(data):
    """PDF export produces non-empty bytes starting with the PDF header."""
    screen, metadata = data

    pdf_bytes = exportScreenToPDF(screen, metadata)

    # Must be non-empty
    assert len(pdf_bytes) > 0, "PDF output must be non-empty"

    # Must be a valid PDF (starts with %PDF-)
    assert pdf_bytes[:5] == b"%PDF-", "PDF must start with %PDF- header"


@given(content_type=_screen_content_type)
@settings(max_examples=10, deadline=None)
def test_property_24_all_screen_types_produce_valid_pdf(content_type):
    """Every ScreenContentType produces a valid PDF."""
    screen = ScreenCapture(
        contentType=content_type,
        htmlContent="Sample content for " + content_type.value,
    )
    metadata = PDFMetadata(
        screenTitle="Test Screen",
        configurationName="Test Config",
        packageName="twinfield",
        templateName="budget",
        generatedAt=datetime.now(timezone.utc),
    )

    pdf_bytes = exportScreenToPDF(screen, metadata)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:5] == b"%PDF-"


def test_property_24_pdf_contains_date_stamp():
    """PDF includes the date stamp from metadata."""
    now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    screen = ScreenCapture(
        contentType=ScreenContentType.CONTROL_TABLE,
        htmlContent="Control totals here",
    )
    metadata = PDFMetadata(
        screenTitle="Control Table",
        configurationName="Twinfield Budget 2026",
        packageName="twinfield",
        templateName="budget",
        generatedAt=now,
    )

    pdf_bytes = exportScreenToPDF(screen, metadata)
    pdf_text = pdf_bytes.decode("latin-1")

    assert "2026-03-28" in pdf_text, "PDF must contain the date stamp"


def test_property_24_pdf_contains_metadata_fields():
    """PDF includes configuration name, package, and template."""
    screen = ScreenCapture(
        contentType=ScreenContentType.DIAGRAM,
        htmlContent="<svg>diagram</svg>",
    )
    metadata = PDFMetadata(
        screenTitle="ArchiMate Diagram",
        configurationName="Exact Budget 2026",
        packageName="exact",
        templateName="budget",
        generatedAt=datetime.now(timezone.utc),
    )

    pdf_bytes = exportScreenToPDF(screen, metadata)
    pdf_text = pdf_bytes.decode("latin-1")

    assert "Exact Budget 2026" in pdf_text, "PDF must contain configuration name"
    assert "exact" in pdf_text, "PDF must contain package name"
    assert "budget" in pdf_text, "PDF must contain template name"


def test_property_24_pdf_contains_screen_content():
    """PDF includes the actual screen content."""
    content = "Entity NL01 Account 4000 Debet 1500"
    screen = ScreenCapture(
        contentType=ScreenContentType.SPREADSHEET,
        htmlContent=content,
    )
    metadata = PDFMetadata(
        screenTitle="Budget Preview",
        generatedAt=datetime.now(timezone.utc),
    )

    pdf_bytes = exportScreenToPDF(screen, metadata)
    pdf_text = pdf_bytes.decode("latin-1")

    assert "Entity NL01 Account 4000 Debet 1500" in pdf_text, (
        "PDF must contain the screen content"
    )


def test_property_24_auto_stamps_date_when_missing():
    """When generatedAt is None, the exporter auto-stamps the current time."""
    screen = ScreenCapture(
        contentType=ScreenContentType.SPREADSHEET,
        htmlContent="test",
    )
    metadata = PDFMetadata(screenTitle="Test", generatedAt=None)

    pdf_bytes = exportScreenToPDF(screen, metadata)
    assert len(pdf_bytes) > 0
    assert metadata.generatedAt is not None, "generatedAt must be auto-stamped"
