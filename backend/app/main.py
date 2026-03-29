"""FastAPI application entry point for the Data Conversion Tool backend.

Mounts template, documentation, and configuration routers.
OpenAPI spec is auto-generated and served at /openapi.json by FastAPI.
All core Pydantic models are registered in the OpenAPI schema so that
the Type Pipeline can generate TypeScript types for the full domain.

The async lifespan handler manages startup (logging, config store) and
graceful shutdown (DuckDB connection release).  Prometheus metrics are
auto-instrumented via prometheus-fastapi-instrumentator.
"""

import inspect
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from backend.app.core import api_models, types
from backend.app.logging_config import setup_logging
from backend.app.persistence.config_store import ConfigStore
from backend.app.routers import configurations, documentation, templates
from backend.app.settings import get_settings


def _collect_models(*modules) -> list[type[BaseModel]]:
    """Return all concrete BaseModel subclasses defined in *modules*."""
    models: list[type[BaseModel]] = []
    for mod in modules:
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, BaseModel)
                and obj is not BaseModel
                and obj.__module__ == mod.__name__
            ):
                models.append(obj)
    return models


def _collect_enums(*modules) -> list[type[Enum]]:
    """Return all str+Enum subclasses defined in *modules*."""
    enums: list[type[Enum]] = []
    for mod in modules:
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, Enum)
                and issubclass(obj, str)
                and obj is not Enum
                and obj.__module__ == mod.__name__
            ):
                enums.append(obj)
    return enums


# Collect every Pydantic model and enum so they appear in the OpenAPI
# schema even before routers reference them in endpoint signatures.
_all_models = _collect_models(types, api_models)
_all_enums = _collect_enums(types)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and graceful shutdown.

    Startup:
      - Read settings from environment variables
      - Configure structured JSON logging
      - Open DuckDB connection and store on app.state

    Shutdown:
      - Release the DuckDB connection so in-flight requests can complete
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    config_store = ConfigStore(db_path=settings.duckdb_path)
    app.state.config_store = config_store
    yield
    config_store.close()


app = FastAPI(
    title="Data Conversion Tool API",
    version="1.0.0",
    description=(
        "Backend API for the Data Conversion Tool: templates, "
        "documentation, and configuration persistence."
    ),
    lifespan=lifespan,
)

app.include_router(
    templates.router,
    prefix="/api/templates",
    tags=["templates"],
)
app.include_router(
    documentation.router,
    prefix="/api/documentation",
    tags=["documentation"],
)
app.include_router(
    configurations.router,
    prefix="/api/configurations",
    tags=["configurations"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def custom_openapi() -> dict[str, Any]:
    """Generate OpenAPI spec with all core domain models included."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    components = schema.setdefault("components", {}).setdefault("schemas", {})

    # Register all Pydantic models
    for model in _all_models:
        json_schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        # Merge the model's own schema
        components.setdefault(model.__name__, json_schema)
        # Merge any $defs produced by nested/referenced models
        for def_name, def_schema in json_schema.pop("$defs", {}).items():
            components.setdefault(def_name, def_schema)

    # Register all enum types
    for enum_cls in _all_enums:
        if enum_cls.__name__ not in components:
            components[enum_cls.__name__] = {
                "type": "string",
                "enum": [e.value for e in enum_cls],
                "title": enum_cls.__name__,
            }

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]
