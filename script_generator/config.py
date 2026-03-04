"""
Configuration for the Script Converter.

Provides the ConverterConfig dataclass that loads settings from
environment variables and validates them at initialization.
"""

import os
from dataclasses import dataclass, field

from script_generator.exceptions import ValidationError

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


@dataclass
class ConverterConfig:
    """
    Configuration for the Script Converter pipeline.

    Reads OPENAI_API_KEY from the environment. Validates log_level
    and llm_model at init time, raising ValidationError on bad values.

    Attributes:
        openai_api_key: OpenAI API key (loaded from OPENAI_API_KEY env var).
        llm_model: LLM model identifier. Defaults to "gpt-4o-mini".
        log_level: Logging level. Defaults to "INFO".
    """

    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        # Load API key from environment if not explicitly provided
        if not self.openai_api_key:
            self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")

        # Validate llm_model is non-empty
        if not self.llm_model or not self.llm_model.strip():
            raise ValidationError("llm_model must not be empty")

        # Validate log_level
        self.log_level = self.log_level.upper()
        if self.log_level not in _VALID_LOG_LEVELS:
            raise ValidationError(
                f"Invalid log_level '{self.log_level}'. "
                f"Must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))}"
            )
