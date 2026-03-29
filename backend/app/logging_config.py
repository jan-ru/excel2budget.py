"""Structured JSON logging configuration (12-Factor: Logs).

Emits all log output as JSON to stdout using python-json-logger.
The application never writes to or manages log files — log routing
is the responsibility of the execution environment.
"""

from __future__ import annotations

import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def setup_logging(log_level: str = "info") -> None:
    """Configure the root logger with JSON structured output to stdout.

    Args:
        log_level: Logging level string (e.g. "debug", "info", "warning", "error").
                   Case-insensitive; uppercased internally.
    """
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "module",
        },
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())
