/**
 * Content sanitization for IronCalc cell values.
 *
 * Prevents XSS by stripping or escaping HTML tags, script elements,
 * event handler attributes, and dangerous URI schemes before rendering
 * cell values in the browser.
 *
 * Requirements: 10.2, 10.3
 */

// Patterns for dangerous HTML/script content
const SCRIPT_TAG_RE = /<\s*script[^>]*>.*?<\s*\/\s*script\s*>/gis;
const STYLE_TAG_RE = /<\s*style[^>]*>.*?<\s*\/\s*style\s*>/gis;
const EVENT_HANDLER_RE = /on\w+\s*=\s*["'][^"']*["']/gi;
const HTML_TAG_RE = /<[^>]+>/gs;
const JAVASCRIPT_URI_RE = /javascript\s*:/gi;
const VBSCRIPT_URI_RE = /vbscript\s*:/gi;
const DATA_URI_SCRIPT_RE = /data\s*:[^,]*;base64/gi;
const EXPRESSION_RE = /expression\s*\(/gi;

/**
 * HTML-entity-encode characters that could enable injection.
 * Encodes &, <, >, ", and '.
 */
function htmlEscape(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

/**
 * Sanitize a string cell value to prevent XSS.
 *
 * Strips all HTML tags, script elements, event handlers, and
 * dangerous URI schemes. The result is a plain-text string safe
 * for rendering in a browser context.
 *
 * @param value - The raw string value from a spreadsheet cell.
 * @returns A sanitized plain-text string with no executable content.
 */
export function sanitizeCellValue(value: string): string {
  if (!value) {
    return value;
  }

  let result = value;

  // 1. Remove <script>...</script> blocks entirely
  result = result.replace(SCRIPT_TAG_RE, "");

  // 2. Remove <style>...</style> blocks
  result = result.replace(STYLE_TAG_RE, "");

  // 3. Remove event handler attributes (onclick=, onerror=, etc.)
  result = result.replace(EVENT_HANDLER_RE, "");

  // 4. Remove all remaining HTML tags
  result = result.replace(HTML_TAG_RE, "");

  // 5. Neutralize dangerous URI schemes
  result = result.replace(JAVASCRIPT_URI_RE, "");
  result = result.replace(VBSCRIPT_URI_RE, "");
  result = result.replace(DATA_URI_SCRIPT_RE, "data:blocked");

  // 6. Remove CSS expression() calls
  result = result.replace(EXPRESSION_RE, "blocked(");

  // 7. HTML-entity-encode any remaining angle brackets or ampersands
  result = htmlEscape(result);

  return result;
}
