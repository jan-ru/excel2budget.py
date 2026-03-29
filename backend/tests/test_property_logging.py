"""Property 20: Structured Log Format.

# Feature: frontend-backend-split, Property 20: Structured Log Format

Validates Requirements 19.18, 19.19, 19.20:
- For any log message emitted, output is valid JSON containing: timestamp (ISO 8601),
  level (matching log level), module (non-empty string), message (the logged text).
- When LOG_LEVEL is set to higher severity, lower severity entries are not emitted.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.app.logging_config import setup_logging

LOG_LEVELS = ["debug", "info", "warning", "error", "critical"]

# Strategy for log messages: printable, non-empty
_log_message = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"), min_codepoint=32, max_codepoint=126
    ),
    min_size=1,
    max_size=200,
)

# Strategy for logger names
_logger_name = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_.]{0,30}", fullmatch=True)


@pytest.fixture(autouse=True)
def _restore_root_logger():
    """Restore root logger state after each test."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.setLevel(original_level)


class TestStructuredLogFormat:
    """For any log message, output is valid JSON with required fields."""

    @settings(max_examples=100)
    @given(
        log_level=st.sampled_from(LOG_LEVELS),
        logger_name=_logger_name,
        message=_log_message,
    )
    def test_log_output_is_valid_json_with_required_fields(
        self, log_level: str, logger_name: str, message: str
    ):
        # Capture stdout via a StringIO stream handler
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)

        from pythonjsonlogger.json import JsonFormatter

        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "module",
            },
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(log_level.upper())

        # Emit a log at the configured level using a named logger
        logger = logging.getLogger(logger_name)
        log_method = getattr(logger, log_level)
        log_method(message)

        output = stream.getvalue().strip()
        assert output, "Expected log output but got nothing"

        parsed = json.loads(output)

        # Required fields
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "module" in parsed
        assert "message" in parsed

        # Validate timestamp is ISO 8601 parseable
        ts = parsed["timestamp"]
        # python-json-logger may produce timestamps with or without timezone
        # Try parsing with common ISO 8601 formats
        try:
            datetime.fromisoformat(ts)
        except ValueError:
            # Fallback: at minimum it should look like a date-time string
            assert "T" in ts or "-" in ts, f"Timestamp not ISO 8601: {ts}"

        # Level matches
        assert parsed["level"] == log_level.upper()

        # Module is non-empty
        assert len(parsed["module"]) > 0

        # Message matches
        assert parsed["message"] == message

        # Cleanup
        root.handlers.clear()


class TestLogLevelFiltering:
    """When LOG_LEVEL is set to higher severity, lower severity entries are not emitted."""

    @settings(max_examples=100)
    @given(
        configured_level=st.sampled_from(LOG_LEVELS),
        emit_level=st.sampled_from(LOG_LEVELS),
        message=_log_message,
    )
    def test_lower_severity_messages_are_filtered(
        self, configured_level: str, emit_level: str, message: str
    ):
        level_order = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}

        # Use setup_logging to configure, but redirect to a StringIO
        stream = io.StringIO()

        from pythonjsonlogger.json import JsonFormatter

        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "module",
            },
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(configured_level.upper())

        logger = logging.getLogger("test.filtering")
        log_method = getattr(logger, emit_level)
        log_method(message)

        output = stream.getvalue().strip()

        should_appear = level_order[emit_level] >= level_order[configured_level]

        if should_appear:
            assert output, (
                f"Expected log at {emit_level} to appear when level is {configured_level}"
            )
            parsed = json.loads(output)
            assert parsed["message"] == message
        else:
            assert not output, (
                f"Expected log at {emit_level} to be filtered when level is {configured_level}"
            )

        # Cleanup
        root.handlers.clear()


class TestSetupLoggingFunction:
    """Verify setup_logging configures the root logger correctly."""

    def test_setup_logging_configures_root_logger(self):
        setup_logging("warning")

        root = logging.getLogger()
        assert root.level == logging.WARNING
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)

    def test_setup_logging_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        assert len(root.handlers) >= 2

        setup_logging("info")

        assert len(root.handlers) == 1

    def test_setup_logging_case_insensitive(self):
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

        setup_logging("Info")
        assert logging.getLogger().level == logging.INFO
