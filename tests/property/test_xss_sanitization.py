"""Property tests for XSS sanitization.

**Validates: Requirement 16.1**

Property 18: XSS sanitization — strings with HTML/script tags produce
output without executable script content.
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.engine.ironcalc.sanitizer import sanitize_cell_value


# ---------------------------------------------------------------------------
# Strategies for generating adversarial HTML/script content
# ---------------------------------------------------------------------------

# Common XSS payload fragments
_SCRIPT_TAGS = [
    "<script>alert('xss')</script>",
    "<SCRIPT>alert(1)</SCRIPT>",
    "<script src='evil.js'></script>",
    "<script\n>alert(1)</script\n>",
    "< script >alert(1)</ script >",
]

_EVENT_HANDLERS = [
    'onerror="alert(1)"',
    "onclick='alert(1)'",
    'onload="fetch(evil)"',
    'onmouseover="alert(1)"',
    'onfocus="alert(1)"',
]

_DANGEROUS_URIS = [
    "javascript:alert(1)",
    "JAVASCRIPT:alert(1)",
    "javascript :alert(1)",
    "vbscript:MsgBox(1)",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
]

_HTML_TAGS = [
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    "<iframe src='evil.html'></iframe>",
    "<div style='background:url(javascript:alert(1))'>",
    "<a href='javascript:alert(1)'>click</a>",
    "<body onload=alert(1)>",
    "<input onfocus=alert(1) autofocus>",
    "<marquee onstart=alert(1)>",
    "<style>body{background:url('javascript:alert(1)')}</style>",
]

_CSS_EXPRESSIONS = [
    "expression(alert(1))",
    "EXPRESSION(alert(1))",
    "expression (alert(1))",
]

known_xss_payloads_st = st.sampled_from(
    _SCRIPT_TAGS + _EVENT_HANDLERS + _DANGEROUS_URIS
    + _HTML_TAGS + _CSS_EXPRESSIONS
)

# Strategy: random text mixed with XSS fragments
mixed_content_st = st.builds(
    lambda prefix, payload, suffix: prefix + payload + suffix,
    prefix=st.text(max_size=30),
    payload=known_xss_payloads_st,
    suffix=st.text(max_size=30),
)

# Strategy: plain text (no HTML)
plain_text_st = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="<>&\"'",
    ),
    max_size=100,
)


# ---------------------------------------------------------------------------
# Property 18 — No executable script content in sanitized output
# ---------------------------------------------------------------------------


@given(payload=known_xss_payloads_st)
@settings(max_examples=200)
def test_property_18_no_script_tags_in_output(payload: str):
    """Sanitized output must not contain <script> tags."""
    result = sanitize_cell_value(payload)
    lower = result.lower()
    assert "<script" not in lower
    assert "</script" not in lower


@given(payload=known_xss_payloads_st)
@settings(max_examples=200)
def test_property_18_no_event_handlers_in_output(payload: str):
    """Sanitized output must not contain on* event handler attributes."""
    result = sanitize_cell_value(payload)
    lower = result.lower()
    # Check common event handlers are not present as executable attributes
    for handler in ["onerror=", "onclick=", "onload=", "onmouseover=",
                     "onfocus=", "onstart="]:
        assert handler not in lower


@given(payload=known_xss_payloads_st)
@settings(max_examples=200)
def test_property_18_no_dangerous_uris_in_output(payload: str):
    """Sanitized output must not contain javascript: or vbscript: URIs."""
    result = sanitize_cell_value(payload)
    lower = result.lower()
    assert "javascript:" not in lower
    assert "vbscript:" not in lower


@given(payload=known_xss_payloads_st)
@settings(max_examples=200)
def test_property_18_no_html_tags_in_output(payload: str):
    """Sanitized output must not contain raw HTML tags (unescaped < >)."""
    result = sanitize_cell_value(payload)
    # After sanitization, no unescaped angle brackets forming tags
    # The sanitizer HTML-escapes remaining < and > so we check for
    # literal < followed by a letter (which would be an HTML tag)
    import re
    assert not re.search(r"<\s*[a-zA-Z]", result)


@given(content=mixed_content_st)
@settings(max_examples=200)
def test_property_18_mixed_content_sanitized(content: str):
    """Mixed content (text + XSS payload) must have all dangerous
    elements removed."""
    result = sanitize_cell_value(content)
    lower = result.lower()
    assert "<script" not in lower
    assert "javascript:" not in lower
    assert "vbscript:" not in lower
    assert not any(
        h in lower
        for h in ["onerror=", "onclick=", "onload=", "onmouseover="]
    )


@given(text=plain_text_st)
@settings(max_examples=200)
def test_property_18_plain_text_preserved(text: str):
    """Plain text without HTML should be preserved (possibly entity-encoded)."""
    result = sanitize_cell_value(text)
    # The sanitized result, when unescaped, should equal the original
    import html as html_mod
    assert html_mod.unescape(result) == text


def test_property_18_empty_string():
    """Empty string should pass through unchanged."""
    assert sanitize_cell_value("") == ""


def test_property_18_none_like():
    """Empty-ish values should pass through."""
    assert sanitize_cell_value("") == ""


@given(payload=st.sampled_from(_CSS_EXPRESSIONS))
@settings(max_examples=50)
def test_property_18_no_css_expressions(payload: str):
    """CSS expression() calls must be neutralized."""
    result = sanitize_cell_value(payload)
    lower = result.lower()
    assert "expression(" not in lower
