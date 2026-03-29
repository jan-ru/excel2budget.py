"""Content sanitization for IronCalc cell values.

Prevents XSS by stripping or escaping HTML tags, script elements,
and event handler attributes before rendering cell values in the browser.

Requirements: 16.1
"""

from __future__ import annotations

import html
import re

# Patterns for dangerous HTML/script content
_SCRIPT_TAG_RE = re.compile(
    r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_STYLE_TAG_RE = re.compile(
    r"<\s*style[^>]*>.*?<\s*/\s*style\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_EVENT_HANDLER_RE = re.compile(
    r"on\w+\s*=\s*[\"'][^\"']*[\"']",
    re.IGNORECASE,
)
_JAVASCRIPT_URI_RE = re.compile(
    r"javascript\s*:", re.IGNORECASE
)
_VBSCRIPT_URI_RE = re.compile(
    r"vbscript\s*:", re.IGNORECASE
)
_DATA_URI_SCRIPT_RE = re.compile(
    r"data\s*:[^,]*;base64", re.IGNORECASE
)
_EXPRESSION_RE = re.compile(
    r"expression\s*\(", re.IGNORECASE
)


def sanitize_cell_value(value: str) -> str:
    """Sanitize a string cell value to prevent XSS.

    Strips all HTML tags, script elements, event handlers, and
    dangerous URI schemes. The result is a plain-text string safe
    for rendering in a browser context.

    Parameters:
        value: The raw string value from a spreadsheet cell.

    Returns:
        A sanitized plain-text string with no executable content.
    """
    if not value:
        return value

    result = value

    # 1. Remove <script>...</script> blocks entirely
    result = _SCRIPT_TAG_RE.sub("", result)

    # 2. Remove <style>...</style> blocks
    result = _STYLE_TAG_RE.sub("", result)

    # 3. Remove event handler attributes (onclick=, onerror=, etc.)
    result = _EVENT_HANDLER_RE.sub("", result)

    # 4. Remove all remaining HTML tags
    result = _HTML_TAG_RE.sub("", result)

    # 5. Neutralize dangerous URI schemes
    result = _JAVASCRIPT_URI_RE.sub("", result)
    result = _VBSCRIPT_URI_RE.sub("", result)
    result = _DATA_URI_SCRIPT_RE.sub("data:blocked", result)

    # 6. Remove CSS expression() calls
    result = _EXPRESSION_RE.sub("blocked(", result)

    # 7. HTML-entity-encode any remaining angle brackets or ampersands
    #    to prevent any residual injection
    result = html.escape(result, quote=True)

    return result
