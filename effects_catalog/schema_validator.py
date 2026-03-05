"""JSON Schema validation for effect parameters using the jsonschema library."""

from __future__ import annotations

import copy
from typing import Any

import jsonschema
from jsonschema import Draft7Validator, ValidationError as JsonSchemaValidationError

from effects_catalog.exceptions import SchemaValidationError


class SchemaValidator:
    """Validates scene instruction parameters against an EffectSkeleton's JSON Schema.

    Uses the jsonschema library (Draft 7) for validation. Applies default values
    from the schema to missing optional fields before returning.
    """

    @staticmethod
    def validate(params: dict, schema: dict) -> dict:
        """Validate params against a JSON Schema and return params with defaults applied.

        Returns a new dict with defaults filled in for missing optional fields.
        Raises SchemaValidationError with field-level details on failure.
        """
        result = copy.deepcopy(params)

        # Apply defaults from schema before validation
        result = SchemaValidator._apply_defaults(result, schema)

        # Validate using jsonschema
        validator = Draft7Validator(schema)
        raw_errors = sorted(validator.iter_errors(result), key=lambda e: list(e.path))

        if raw_errors:
            errors = SchemaValidator._format_errors(raw_errors)
            raise SchemaValidationError(errors)

        return result

    @staticmethod
    def _apply_defaults(params: dict, schema: dict) -> dict:
        """Apply default values from schema properties to missing fields."""
        result = copy.deepcopy(params)
        properties = schema.get("properties", {})

        for field_name, field_schema in properties.items():
            if field_name not in result and "default" in field_schema:
                result[field_name] = copy.deepcopy(field_schema["default"])

        return result

    @staticmethod
    def _format_errors(raw_errors: list[JsonSchemaValidationError]) -> list[dict]:
        """Convert jsonschema ValidationErrors to field-level error dicts."""
        errors: list[dict] = []

        for error in raw_errors:
            field = SchemaValidator._extract_field(error)
            message = error.message
            error_type = SchemaValidator._classify_error(error)

            errors.append({
                "field": field,
                "message": message,
                "type": error_type,
            })

        return errors

    @staticmethod
    def _extract_field(error: JsonSchemaValidationError) -> str:
        """Extract a human-readable field path from a jsonschema error."""
        if error.path:
            parts = []
            for part in error.path:
                if isinstance(part, int):
                    parts.append(f"[{part}]")
                else:
                    parts.append(str(part))
            # Join with dots, but array indices attach directly
            result = ""
            for part in parts:
                if part.startswith("["):
                    result += part
                elif result:
                    result += "." + part
                else:
                    result = part
            return result

        # For required field errors, extract the field name from the validator
        if error.validator == "required":
            # The message is like "'field' is a required property"
            for field in error.validator_value:
                if field in error.message:
                    return field

        return "root"

    @staticmethod
    def _classify_error(error: JsonSchemaValidationError) -> str:
        """Map jsonschema validator names to our error type strings."""
        mapping = {
            "required": "required",
            "type": "type",
            "enum": "enum",
            "minimum": "minimum",
            "maximum": "maximum",
            "minItems": "minItems",
            "maxItems": "maxItems",
            "minLength": "minLength",
            "maxLength": "maxLength",
            "pattern": "pattern",
            "format": "format",
        }
        return mapping.get(error.validator, "validation")
