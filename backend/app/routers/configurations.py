"""Configuration CRUD API router.

Reads the ConfigStore from ``request.app.state.config_store`` which is
set up by the lifespan handler in ``main.py``.  For tests that don't use
the lifespan, ``set_store()`` can inject a store directly.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.app.core.api_models import (
    ConfigurationListResponse,
    CreateConfigurationRequest,
    CustomerConfiguration,
    UpdateConfigurationRequest,
)
from backend.app.persistence.config_store import ConfigStore

router = APIRouter()

_store_override: ConfigStore | None = None


def _get_store(request: Request) -> ConfigStore:
    """Return the active ConfigStore.

    Prefers an explicit override (set via ``set_store``, used by tests),
    then falls back to ``request.app.state.config_store`` (set by lifespan).
    """
    if _store_override is not None:
        return _store_override
    return request.app.state.config_store


def set_store(store: ConfigStore | None) -> None:
    """Replace the module-level store override (used by tests)."""
    global _store_override
    _store_override = store


@router.get("", response_model=ConfigurationListResponse)
def list_configurations(request: Request) -> ConfigurationListResponse:
    """List all saved configurations."""
    configs = _get_store(request).list_all()
    return ConfigurationListResponse(configurations=configs)


@router.post(
    "", response_model=CustomerConfiguration, status_code=status.HTTP_201_CREATED
)
def create_configuration(
    request: Request, req: CreateConfigurationRequest
) -> CustomerConfiguration:
    """Create a new configuration."""
    store = _get_store(request)
    if store.get(req.name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration '{req.name}' already exists",
        )
    return store.create(req)


@router.get("/{name}", response_model=CustomerConfiguration)
def get_configuration(request: Request, name: str) -> CustomerConfiguration:
    """Get a configuration by name."""
    config = _get_store(request).get(name)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return config


@router.put("/{name}", response_model=CustomerConfiguration)
def update_configuration(
    request: Request, name: str, req: UpdateConfigurationRequest
) -> CustomerConfiguration:
    """Update an existing configuration."""
    config = _get_store(request).update(name, req)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return config


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_configuration(request: Request, name: str) -> Response:
    """Delete a configuration by name."""
    if not _get_store(request).delete(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
