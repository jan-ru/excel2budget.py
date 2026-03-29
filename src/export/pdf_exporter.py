"""PDF exporter for screen content.

Implements exportScreenToPDF(screenContent, metadata) producing PDF bytes.
Includes date stamp, configuration name, accounting package, and template
in the PDF. Supports screen types: spreadsheet, diagram, control table.

Requirements: 20.1, 20.2, 20.3, 20.4
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from fpdf import FPDF

from src.core.types import (
    PDFMetadata,
    ScreenCapture,
    ScreenContentType,
)


def _sanitize_latin1(text: str) -> str:
    """Replace characters outside latin-1 range with '?' for built-in fonts."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def exportScreenToPDF(screenContent: ScreenCapture, metadata: PDFMetadata) -> bytes:
    """Export screen content to a PDF document.

    Args:
        screenContent: The captured screen content (HTML/SVG text) with its type.
        metadata: PDF metadata including title, configuration, package, template, date.

    Returns:
        Non-empty bytes representing a valid PDF document.
    """
    if metadata.generatedAt is None:
        metadata.generatedAt = datetime.now(timezone.utc)

    pdf = FPDF()
    pdf.compress = False  # keep text searchable in raw PDF bytes
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Header with metadata ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(
        0, 10, _sanitize_latin1(metadata.screenTitle or "Untitled"),
        new_x="LMARGIN", new_y="NEXT",
    )

    pdf.set_font("Helvetica", "", 10)
    date_str = metadata.generatedAt.strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 6, f"Date: {date_str}", new_x="LMARGIN", new_y="NEXT")

    if metadata.configurationName:
        pdf.cell(
            0, 6,
            _sanitize_latin1(f"Configuration: {metadata.configurationName}"),
            new_x="LMARGIN", new_y="NEXT",
        )
    if metadata.packageName:
        pdf.cell(
            0, 6,
            _sanitize_latin1(f"Accounting Package: {metadata.packageName}"),
            new_x="LMARGIN", new_y="NEXT",
        )
    if metadata.templateName:
        pdf.cell(
            0, 6,
            _sanitize_latin1(f"Template: {metadata.templateName}"),
            new_x="LMARGIN", new_y="NEXT",
        )

    pdf.cell(
        0, 6,
        f"Content Type: {screenContent.contentType.value}",
        new_x="LMARGIN", new_y="NEXT",
    )

    # Separator line
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # --- Screen content body ---
    pdf.set_font("Courier", "", 9)
    content = _sanitize_latin1(screenContent.htmlContent or "")
    pdf.multi_cell(0, 5, content)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
