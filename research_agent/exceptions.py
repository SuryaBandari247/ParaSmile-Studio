"""
Custom exceptions for the Research Agent.

This module defines the exception hierarchy for all research agent errors,
providing specific exception types for different failure scenarios with
appropriate context and error information.
"""

from datetime import datetime
from typing import List


class ResearchAgentError(Exception):
    """Base exception for all research agent errors."""
    pass


class AuthenticationError(ResearchAgentError):
    """Raised when API key is missing or invalid."""
    pass


class QuotaExceededError(ResearchAgentError):
    """Raised when YouTube API quota is exhausted."""
    
    def __init__(self, reset_at: datetime):
        """
        Initialize QuotaExceededError with reset timestamp.
        
        Args:
            reset_at: Timestamp when the quota will reset
        """
        self.reset_at = reset_at
        super().__init__(f"API quota exceeded. Resets at {reset_at.isoformat()}")


class NetworkError(ResearchAgentError):
    """Raised when network connectivity is lost."""
    pass


class ParseError(ResearchAgentError):
    """Raised when API response parsing fails."""
    
    def __init__(self, raw_response: str):
        """
        Initialize ParseError with raw response data.
        
        Args:
            raw_response: The raw API response that failed to parse
        """
        self.raw_response = raw_response
        super().__init__("Failed to parse API response")


class SchemaValidationError(ResearchAgentError):
    """Raised when output data fails schema validation."""
    
    def __init__(self, violations: List[str]):
        """
        Initialize SchemaValidationError with violation details.
        
        Args:
            violations: List of schema validation violations
        """
        self.violations = violations
        super().__init__(f"Schema validation failed: {', '.join(violations)}")


class CacheCorruptionError(ResearchAgentError):
    """Raised when cache file is corrupted or unreadable."""
    pass


class SourceUnavailableError(ResearchAgentError):
    """Raised when a data source is unreachable or returns an error."""

    def __init__(self, source_name: str, message: str = ""):
        """
        Initialize SourceUnavailableError with the source name.

        Args:
            source_name: Name of the unavailable data source (e.g., 'Google Trends', 'Reddit')
            message: Optional additional error message
        """
        self.source_name = source_name
        msg = f"Data source unavailable: {source_name}"
        if message:
            msg += f" - {message}"
        super().__init__(msg)


class PitchGenerationError(ResearchAgentError):
    """Raised when GPT-4o-mini pitch generation fails."""
    pass
