"""Property 1: Type Pipeline Round-Trip.

Verify that every Pydantic model in backend/app/core/types.py appears in the
generated OpenAPI spec with matching fields.

Validates: Requirements 3.1
"""

import inspect
from enum import Enum

from pydantic import BaseModel

from backend.app.core import types
from backend.app.main import app


def _get_openapi_schemas() -> dict:
    """Return the schemas dict from the app's OpenAPI spec."""
    # Reset cached schema so we always get a fresh one
    app.openapi_schema = None
    spec = app.openapi()
    return spec.get("components", {}).get("schemas", {})


def _collect_types_models() -> list[type[BaseModel]]:
    """Collect all concrete BaseModel subclasses defined in types.py."""
    return [
        obj
        for _name, obj in inspect.getmembers(types, inspect.isclass)
        if issubclass(obj, BaseModel)
        and obj is not BaseModel
        and obj.__module__ == types.__name__
    ]


def _collect_types_enums() -> list[type[Enum]]:
    """Collect all str+Enum subclasses defined in types.py."""
    return [
        obj
        for _name, obj in inspect.getmembers(types, inspect.isclass)
        if issubclass(obj, Enum)
        and issubclass(obj, str)
        and obj is not Enum
        and obj.__module__ == types.__name__
    ]


def _pydantic_field_names(model: type[BaseModel]) -> set[str]:
    """Return the set of field names declared on a Pydantic model."""
    return set(model.model_fields.keys())


def _openapi_field_names(schema: dict) -> set[str]:
    """Extract field names from an OpenAPI schema object.

    Handles regular 'properties' schemas as well as discriminated unions
    represented via 'oneOf'/'anyOf' (which have no direct properties).
    """
    props = schema.get("properties", {})
    if props:
        return set(props.keys())
    return set()


class TestTypePipelineRoundTrip:
    """Every Pydantic model in types.py must appear in the OpenAPI spec."""

    def test_all_models_present_in_openapi(self):
        """Each model class name must be a key in components/schemas."""
        schemas = _get_openapi_schemas()
        models = _collect_types_models()

        missing = [m.__name__ for m in models if m.__name__ not in schemas]
        assert not missing, f"Models missing from OpenAPI spec: {missing}"

    def test_model_fields_match_openapi(self):
        """For each model, every Pydantic field must appear in the OpenAPI schema."""
        schemas = _get_openapi_schemas()
        models = _collect_types_models()

        mismatches: list[str] = []
        for model in models:
            schema = schemas.get(model.__name__)
            if schema is None:
                mismatches.append(f"{model.__name__}: not in OpenAPI spec")
                continue

            pydantic_fields = _pydantic_field_names(model)
            openapi_fields = _openapi_field_names(schema)

            # Skip combinator schemas (oneOf/anyOf) — they don't have
            # direct properties; their variants are checked individually.
            if not openapi_fields and ("oneOf" in schema or "anyOf" in schema):
                continue

            missing_in_openapi = pydantic_fields - openapi_fields
            if missing_in_openapi:
                mismatches.append(
                    f"{model.__name__}: fields {missing_in_openapi} missing from OpenAPI"
                )

        assert not mismatches, "Field mismatches:\n" + "\n".join(mismatches)

    def test_no_extra_openapi_fields(self):
        """OpenAPI schema should not have properties absent from the Pydantic model."""
        schemas = _get_openapi_schemas()
        models = _collect_types_models()

        extras: list[str] = []
        for model in models:
            schema = schemas.get(model.__name__)
            if schema is None:
                continue

            openapi_fields = _openapi_field_names(schema)
            if not openapi_fields and ("oneOf" in schema or "anyOf" in schema):
                continue

            pydantic_fields = _pydantic_field_names(model)
            extra = openapi_fields - pydantic_fields
            if extra:
                extras.append(f"{model.__name__}: extra OpenAPI fields {extra}")

        assert not extras, "Extra fields in OpenAPI:\n" + "\n".join(extras)

    def test_enum_types_present(self):
        """All str Enum types from types.py should appear in the OpenAPI spec."""
        schemas = _get_openapi_schemas()
        enum_classes = _collect_types_enums()

        missing = [e.__name__ for e in enum_classes if e.__name__ not in schemas]
        assert not missing, f"Enum types missing from OpenAPI spec: {missing}"
