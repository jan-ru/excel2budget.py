"""Configuration CRUD API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from backend.app.core.api_models import (
    ConfigurationListResponse,
    CreateConfigurationRequest,
    CustomerConfiguration,
    UpdateConfigurationRequest,
)
from backend.app.persistence.config_store import ConfigStore

router = APIRouter()

_store: ConfigStore | None = None


def _get_store() -> ConfigStore:
    global _store
    if _store is None:
        _store = ConfigStore()
    return _store


def set_store(store: ConfigStore) -> None:
    """Replace the module-level store (used by tests)."""
    global _store
    _store = store


@router.get("", response_model=ConfigurationListResponse)
def list_configurations() -> ConfigurationListResponse:
    """List all saved configurations."""
    configs = _get_store().list_all()
    return ConfigurationListResponse(configurations=configs)


@router.post(
    "", response_model=CustomerConfiguration, status_code=status.HTTP_201_CREATED
)
def create_configuration(req: CreateConfigurationRequest) -> CustomerConfiguration:
    """Create a new configuration."""
    store = _get_store()
    if store.get(req.name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration '{req.name}' already exists",
        )
    return store.create(req)


@router.get("/{name}", response_model=CustomerConfiguration)
def get_configuration(name: str) -> CustomerConfiguration:
    """Get a configuration by name."""
    config = _get_store().get(name)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return config


@router.put("/{name}", response_model=CustomerConfiguration)
def update_configuration(
    name: str, req: UpdateConfigurationRequest
) -> CustomerConfiguration:
    """Update an existing configuration."""
    config = _get_store().update(name, req)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return config


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_configuration(name: str) -> Response:
    """Delete a configuration by name."""
    if not _get_store().delete(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration '{name}' not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
