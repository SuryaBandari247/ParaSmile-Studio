# Design Document: Stock Footage Visuals

## Overview

This module extends the Asset Orchestrator to produce real YouTube-quality video by combining stock footage from Pexels with FFmpeg-based text overlays. Manim remains for data charts/code, but stock footage becomes the primary visual engine for narrative scenes.

### Core Objectives

1. **Pexels Integration**: Search and download HD stock video clips by keyword
2. **Smart Keyword Extraction**: Use GPT-4o-mini to derive visual search terms from narration text
3. **FFmpeg Composition**: Overlay text, stats, and quotes on stock footage with dark scrim for readability
4. **Seamless Orchestration**: Stock and Manim scenes coexist in the same batch — no config changes needed

### Design Principles

- **Additive**: New code only — no breaking changes to existing Manim pipeline
- **Graceful Degradation**: If Pexels returns nothing, fall back to solid-color background with text
- **Cache-First**: Downloaded clips and extracted keywords are cached to minimize API calls
- **Consistent Output**: All scenes output 1080p/30fps MP4 regardless of source (Manim or stock)

## Architecture

### System Components

```
Video Script JSON
       │
       ▼
┌─────────────────────────────────────────────┐
│            Asset Orchestrator                │
│                                             │
│  ┌─────────────┐    ┌───────────────────┐   │
│  │ Scene Router │───▶│ Manim Pipeline    │   │
│  │ (type check) │    │ (existing)        │   │
│  └──────┬──────┘    └───────────────────┘   │
│         │                                    │
│         ▼                                    │
│  ┌───────────────────────────────────────┐   │
│  │ Stock Footage Pipeline (NEW)          │   │
│  │                                       │   │
│  │  Keyword Extractor                    │   │
│  │       │                               │   │
│  │       ▼                               │   │
│  │  PexelsClient ──▶ Download Cache      │   │
│  │       │                               │   │
│  │       ▼                               │   │
│  │  FFmpegCompositor                     │   │
│  │  (text overlay + dark scrim)          │   │
│  └───────────────────────────────────────┘   │
│                                             │
│         ▼                                    │
│    Composed MP4 (1080p/30fps)               │
└─────────────────────────────────────────────┘
```

### Data Flow

1. Orchestrator receives a Visual_Instruction
2. Scene Router checks if `type` starts with `stock_` → stock pipeline, else → Manim pipeline
3. Stock pipeline: extract keywords → search Pexels → download best clip → FFmpeg composite text → return MP4 path
4. If Pexels returns no results → generate solid-color background → composite text → return MP4 path

## Components and Interfaces

### PexelsClient

```python
# asset_orchestrator/pexels_client.py

class PexelsClient:
    """Search and download stock video clips from Pexels API."""

    def __init__(self, api_key: str | None = None, cache_dir: str = "output/stock_cache"):
        """
        Args:
            api_key: Pexels API key. Falls back to PEXELS_API_KEY env var.
            cache_dir: Local directory for caching downloaded clips.
        Raises:
            ConfigurationError: If no API key is available.
        """

    def search_videos(self, query: str, per_page: int = 5, min_duration: int = 5) -> list[dict]:
        """
        Search Pexels for stock videos matching the query.

        Args:
            query: Search keywords (e.g., "person filing taxes").
            per_page: Max results to return.
            min_duration: Minimum video duration in seconds.

        Returns:
            List of video result dicts with keys: id, url, duration, width, height, video_files.
            Empty list if no results.
        """

    def download_video(self, video_result: dict, filename: str | None = None) -> str:
        """
        Download the best-quality video file (preferring 1080p+).

        Args:
            video_result: A single result dict from search_videos().
            filename: Optional filename. Auto-generated from video ID if None.

        Returns:
            Absolute path to the downloaded MP4 file.
        """

    def search_and_download(self, query: str, min_duration: int = 5) -> str | None:
        """
        Convenience: search for a query and download the best result.

        Returns:
            Absolute path to downloaded clip, or None if no results.
        """
```

### KeywordExtractor

```python
# asset_orchestrator/keyword_extractor.py

class KeywordExtractor:
    """Extract visual search keywords from scene narration text."""

    def __init__(self, use_llm: bool = True):
        """
        Args:
            use_llm: If True, use GPT-4o-mini for smart extraction.
                     Falls back to simple noun extraction on failure.
        """

    def extract(self, narration_text: str, title: str = "") -> list[str]:
        """
        Extract 2-4 visual search keywords from narration.

        Args:
            narration_text: The scene's narration/script text.
            title: The scene title (optional context).

        Returns:
            List of 2-4 keyword strings suitable for Pexels search.
        """

    def _extract_with_llm(self, narration_text: str, title: str) -> list[str]:
        """Use GPT-4o-mini to extract visual keywords."""

    def _extract_simple(self, narration_text: str, title: str) -> list[str]:
        """Fallback: extract nouns using simple heuristics."""
```

### FFmpegCompositor

```python
# asset_orchestrator/ffmpeg_compositor.py

class FFmpegCompositor:
    """Compose stock footage with text overlays using FFmpeg."""

    def __init__(self, output_dir: str = "output/composed_stock"):
        """
        Args:
            output_dir: Directory for composed output files.
        """

    def compose_text_overlay(
        self,
        video_path: str,
        heading: str = "",
        body: str = "",
        position: str = "center",
        duration: float | None = None,
        output_path: str | None = None,
    ) -> str:
        """
        Overlay heading + body text on stock footage with dark scrim.

        Args:
            video_path: Path to stock video clip.
            heading: Large heading text.
            body: Smaller body text below heading.
            position: Text position — "top", "center", or "bottom".
            duration: Target duration in seconds. Trims/loops video to match.
            output_path: Optional output path.

        Returns:
            Absolute path to composed MP4.
        """

    def compose_stat_overlay(
        self,
        video_path: str,
        value: str,
        label: str,
        subtitle: str = "",
        duration: float | None = None,
        output_path: str | None = None,
    ) -> str:
        """
        Overlay a large stat value + label on stock footage.

        Args:
            video_path: Path to stock video clip.
            value: The big number/stat (e.g., "$10,000").
            label: Label below the stat (e.g., "UNEXPECTED TAX BILL").
            subtitle: Optional smaller text below label.
            duration: Target duration in seconds.
            output_path: Optional output path.

        Returns:
            Absolute path to composed MP4.
        """

    def compose_quote_overlay(
        self,
        video_path: str,
        quote: str,
        attribution: str = "",
        duration: float | None = None,
        output_path: str | None = None,
    ) -> str:
        """
        Overlay a styled quote with attribution on stock footage.

        Args:
            video_path: Path to stock video clip.
            quote: The quote text.
            attribution: Attribution line (e.g., "— Reddit user").
            duration: Target duration in seconds.
            output_path: Optional output path.

        Returns:
            Absolute path to composed MP4.
        """

    def generate_solid_background(
        self,
        duration: float = 8.0,
        color: str = "0x1a1a2e",
        output_path: str | None = None,
    ) -> str:
        """
        Generate a solid-color background video (fallback when no stock footage).

        Returns:
            Absolute path to the generated MP4.
        """

    def _build_scrim_filter(self, opacity: float = 0.5) -> str:
        """Build FFmpeg filter for semi-transparent dark overlay."""

    def _build_text_filter(
        self,
        text: str,
        fontsize: int = 48,
        y_position: str = "(h-text_h)/2",
        fontcolor: str = "white",
    ) -> str:
        """Build FFmpeg drawtext filter string."""
```

### Stock Scene Types

```python
# asset_orchestrator/stock_scenes.py

class StockVideoScene(BaseScene):
    """Stock footage background with optional title overlay."""

class StockWithTextScene(BaseScene):
    """Stock footage with heading + body text overlay."""

class StockWithStatScene(BaseScene):
    """Stock footage with large stat value + label overlay."""

class StockQuoteScene(BaseScene):
    """Stock footage with styled quote + attribution overlay."""
```

### Orchestrator Extension

The existing `AssetOrchestrator.process_instruction()` is extended to detect stock scene types and route them through the stock pipeline:

```python
# In orchestrator.py — modified process_instruction

STOCK_SCENE_TYPES = {"stock_video", "stock_with_text", "stock_with_stat", "stock_quote"}

def process_instruction(self, instruction, audio_path=None):
    inst_type = instruction.get("type", "unknown")

    if inst_type in STOCK_SCENE_TYPES:
        return self._process_stock_instruction(instruction, audio_path)
    else:
        # existing Manim pipeline
        ...

def _process_stock_instruction(self, instruction, audio_path=None):
    """Process a stock footage scene."""
    # 1. Extract keywords (from data.keywords or auto-extract from narration)
    # 2. Search Pexels
    # 3. Download best clip (or generate solid background fallback)
    # 4. Compose text overlay via FFmpegCompositor
    # 5. Optionally compose with narration audio
    # 6. Return result dict
```

## Data Models

### Stock Scene Data Schemas

```python
# stock_video
{"title": "optional title", "keywords": ["optional", "search", "terms"]}

# stock_with_text
{"heading": "Main Heading", "body": "Body text content", "keywords": ["optional"]}

# stock_with_stat
{"value": "$10,000", "label": "UNEXPECTED TAX BILL", "subtitle": "optional", "keywords": ["optional"]}

# stock_quote
{"quote": "The quote text here", "attribution": "— Source", "keywords": ["optional"]}
```

### PexelsVideoResult

```python
@dataclass
class PexelsVideoResult:
    id: int
    url: str
    duration: int          # seconds
    width: int
    height: int
    video_files: list[dict]  # [{link, quality, width, height, fps}]
```

## Error Handling

### New Exceptions

```python
class ConfigurationError(AssetOrchestratorError):
    """Raised when required configuration (API keys) is missing."""

class StockFootageError(AssetOrchestratorError):
    """Raised when stock footage search/download fails unrecoverably."""
```

### Fallback Strategy

1. Pexels returns no results → generate solid-color background → continue with text overlay
2. Pexels API error (rate limit, network) → log warning → fall back to solid-color background
3. FFmpeg composition fails → raise CompositionError (existing behavior)
4. Keyword extraction LLM fails → fall back to simple noun extraction
5. No API key → raise ConfigurationError at init time

## Testing Strategy

### Unit Tests

- `test_pexels_client.py`: Mock HTTP responses, test search/download/cache, test missing API key
- `test_keyword_extractor.py`: Test LLM extraction, test fallback, test caching
- `test_ffmpeg_compositor.py`: Mock subprocess, test filter construction, test solid background generation
- `test_stock_scenes.py`: Test scene registration, test data schema validation
- `test_orchestrator_stock.py`: Test routing logic, test mixed batch (stock + Manim), test fallback

### Mocking Strategy

- Mock `requests.get` for Pexels API calls
- Mock `subprocess.run` for FFmpeg calls
- Mock OpenAI client for keyword extraction
- Use temporary directories for cache and output
