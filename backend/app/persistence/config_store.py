"""DuckDB-based persistence layer for customer configurations."""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from backend.app.core.api_models import (
    CreateConfigurationRequest,
    CustomerConfiguration,
    UpdateConfigurationRequest,
)


def _utcnow_naive() -> datetime:
    """Return current UTC time as a naive datetime (no tzinfo).

    DuckDB's TIMESTAMP type is timezone-naive. Storing naive UTC avoids
    implicit local-time conversion on retrieval.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConfigStore:
    """CRUD operations for customer configurations backed by DuckDB."""

    def __init__(self, db_path: str = "data/config.duckdb") -> None:
        self.db_path = db_path
        self._conn = duckdb.connect(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the configurations table if it doesn't exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_configurations (
                name          VARCHAR PRIMARY KEY,
                package_name  VARCHAR NOT NULL,
                template_name VARCHAR NOT NULL,
                budgetcode    VARCHAR NOT NULL,
                year          INTEGER NOT NULL,
                created_at    TIMESTAMP NOT NULL,
                updated_at    TIMESTAMP NOT NULL
            )
            """
        )

    def create(self, req: CreateConfigurationRequest) -> CustomerConfiguration:
        """Insert a new configuration and return it."""
        now = _utcnow_naive()
        self._conn.execute(
            """
            INSERT INTO customer_configurations
                (name, package_name, template_name, budgetcode, year, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                req.name,
                req.packageName,
                req.templateName,
                req.budgetcode,
                req.year,
                now,
                now,
            ],
        )
        return CustomerConfiguration(
            name=req.name,
            packageName=req.packageName,
            templateName=req.templateName,
            budgetcode=req.budgetcode,
            year=req.year,
            createdAt=now,
            updatedAt=now,
        )

    def get(self, name: str) -> CustomerConfiguration | None:
        """Return a configuration by name, or None if not found."""
        result = self._conn.execute(
            "SELECT name, package_name, template_name, budgetcode, year, created_at, updated_at "
            "FROM customer_configurations WHERE name = ?",
            [name],
        ).fetchone()
        if result is None:
            return None
        return self._row_to_model(result)

    def list_all(self) -> list[CustomerConfiguration]:
        """Return all stored configurations."""
        rows = self._conn.execute(
            "SELECT name, package_name, template_name, budgetcode, year, created_at, updated_at "
            "FROM customer_configurations ORDER BY name"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def update(
        self, name: str, req: UpdateConfigurationRequest
    ) -> CustomerConfiguration | None:
        """Update fields on an existing configuration. Returns None if not found."""
        existing = self.get(name)
        if existing is None:
            return None

        now = _utcnow_naive()
        new_pkg = (
            req.packageName if req.packageName is not None else existing.packageName
        )
        new_tpl = (
            req.templateName if req.templateName is not None else existing.templateName
        )
        new_bc = req.budgetcode if req.budgetcode is not None else existing.budgetcode
        new_yr = req.year if req.year is not None else existing.year

        self._conn.execute(
            """
            UPDATE customer_configurations
            SET package_name = ?, template_name = ?, budgetcode = ?, year = ?, updated_at = ?
            WHERE name = ?
            """,
            [new_pkg, new_tpl, new_bc, new_yr, now, name],
        )
        return CustomerConfiguration(
            name=name,
            packageName=new_pkg,
            templateName=new_tpl,
            budgetcode=new_bc,
            year=new_yr,
            createdAt=existing.createdAt,
            updatedAt=now,
        )

    def delete(self, name: str) -> bool:
        """Delete a configuration by name. Returns True if it existed."""
        existing = self.get(name)
        if existing is None:
            return False
        self._conn.execute("DELETE FROM customer_configurations WHERE name = ?", [name])
        return True

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()

    @staticmethod
    def _row_to_model(row: tuple) -> CustomerConfiguration:
        name, pkg, tpl, bc, yr, created, updated = row
        return CustomerConfiguration(
            name=name,
            packageName=pkg,
            templateName=tpl,
            budgetcode=bc,
            year=yr,
            createdAt=created,
            updatedAt=updated,
        )
