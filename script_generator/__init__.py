"""
Script Generator - Converts raw script text to structured VideoScript JSON.

This module accepts raw script text (from Gemini Pro or any source), uses
GPT-4o-mini to convert it into a structured VideoScript JSON format, validates
visual instructions against the Asset Orchestrator schema, and returns a
render-ready script.
"""

__version__ = "0.1.0"

from script_generator.converter import ScriptConverter
from script_generator.models import VideoScript, SceneBlock
from script_generator.config import ConverterConfig
from script_generator.exceptions import (
    ScriptConverterError,
    ValidationError,
    ParseError,
    AuthenticationError,
    LLMError,
)
from script_generator.serializer import ScriptSerializer
from script_generator.validator import Validator

__all__ = [
    "ScriptConverter",
    "VideoScript",
    "SceneBlock",
    "ConverterConfig",
    "ScriptConverterError",
    "ValidationError",
    "ParseError",
    "AuthenticationError",
    "LLMError",
    "ScriptSerializer",
    "Validator",
]
