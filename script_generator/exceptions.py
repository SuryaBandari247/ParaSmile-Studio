"""
Custom exceptions for the Script Converter.

Defines the exception hierarchy for all script converter errors,
providing specific exception types for different failure scenarios.
All exceptions inherit from ScriptConverterError for unified catching.
"""


class ScriptConverterError(Exception):
    """Base exception for all script converter errors."""
    pass


class ValidationError(ScriptConverterError):
    """Raised when input is invalid or visual instructions fail validation."""
    pass


class ParseError(ScriptConverterError):
    """Raised when LLM response or JSON parsing fails."""
    pass


class AuthenticationError(ScriptConverterError):
    """Raised when API key is missing or invalid."""
    pass


class LLMError(ScriptConverterError):
    """Raised for non-retryable OpenAI API errors."""
    pass
