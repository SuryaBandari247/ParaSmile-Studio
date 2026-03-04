"""
Asset Orchestrator - Transforms visual instructions into production-ready video assets.

This module sits between the Script Generator and the final video assembly pipeline
in Calm Capitalist. It maps visual instructions to Manim Scene
classes for code-generated animations, provides reusable chart templates, and wraps
FFmpeg for compositing audio with rendered MP4 animations.

All visuals are code-generated — no generic AI stock footage.
"""

__version__ = "0.1.0"

from asset_orchestrator.config import (
    BatchResult,
    CompositionConfig,
    RenderConfig,
    VisualInstruction,
)
from asset_orchestrator.exceptions import (
    AssetOrchestratorError,
    CompositionError,
    ConfigurationError,
    DuplicateSceneTypeError,
    ParseError,
    RenderError,
    StockFootageError,
    UnknownSceneTypeError,
    ValidationError,
)
from asset_orchestrator.ffmpeg_wrapper import FFmpegWrapper
from asset_orchestrator.ffmpeg_compositor import FFmpegCompositor
from asset_orchestrator.keyword_extractor import KeywordExtractor
from asset_orchestrator.orchestrator import AssetOrchestrator
from asset_orchestrator.pexels_client import PexelsClient
from asset_orchestrator.renderer import Renderer
from asset_orchestrator.scene_mapper import SceneMapper
from asset_orchestrator.scene_registry import SceneRegistry

__all__: list[str] = [
    # Core components
    "AssetOrchestrator",
    "SceneMapper",
    "SceneRegistry",
    "Renderer",
    "FFmpegWrapper",
    "FFmpegCompositor",
    "PexelsClient",
    "KeywordExtractor",
    # Data models / config
    "RenderConfig",
    "CompositionConfig",
    "VisualInstruction",
    "BatchResult",
    # Exceptions
    "AssetOrchestratorError",
    "ValidationError",
    "UnknownSceneTypeError",
    "DuplicateSceneTypeError",
    "RenderError",
    "CompositionError",
    "ParseError",
    "ConfigurationError",
    "StockFootageError",
]
