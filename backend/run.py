"""Uvicorn entry point for the Data Conversion Tool backend.

Reads host, port, and log_level from environment variables via the
Settings module and starts the ASGI server.

Usage:
    python backend/run.py
    python -m backend.run
"""

import uvicorn

from backend.app.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
