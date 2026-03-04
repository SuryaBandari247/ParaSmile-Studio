"""Script JSON Schema — Pydantic models with enums for Swagger documentation.

These models define the structure of the video script JSON that gets imported
or generated. They appear in the OpenAPI/Swagger docs with all enum values
visible for easy reference when authoring scripts.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class VisualType(str, Enum):
    """All supported visual instruction types."""
    # Stock footage scenes (Pexels pipeline)
    stock_video = "stock_video"
    stock_with_text = "stock_with_text"
    stock_with_stat = "stock_with_stat"
    stock_quote = "stock_quote"
    social_card = "social_card"
    # Data visualization
    data_chart = "data_chart"
    # Manim-based scenes
    bar_chart = "bar_chart"
    line_chart = "line_chart"
    pie_chart = "pie_chart"
    code_snippet = "code_snippet"
    text_overlay = "text_overlay"
    # YouTube-style scenes
    reddit_post = "reddit_post"
    stat_callout = "stat_callout"
    quote_block = "quote_block"
    section_title = "section_title"
    bullet_reveal = "bullet_reveal"
    comparison = "comparison"
    fullscreen_statement = "fullscreen_statement"


class ChartType(str, Enum):
    """Chart subtypes for data_chart visual type."""
    bar = "bar"
    line = "line"
    area = "area"
    horizontal_bar = "horizontal_bar"
    grouped_bar = "grouped_bar"
    pie = "pie"
    donut = "donut"
    timeseries = "timeseries"


class Transition(str, Enum):
    """All supported FFmpeg xfade transitions."""
    # Clean
    none = "none"
    fade = "fade"
    fadeblack = "fadeblack"
    fadewhite = "fadewhite"
    dissolve = "dissolve"
    # Smooth
    smoothleft = "smoothleft"
    smoothright = "smoothright"
    smoothup = "smoothup"
    smoothdown = "smoothdown"
    # Directional
    wipeleft = "wipeleft"
    wiperight = "wiperight"
    wipeup = "wipeup"
    wipedown = "wipedown"
    slideleft = "slideleft"
    slideright = "slideright"
    slideup = "slideup"
    slidedown = "slidedown"
    # Geometric
    circlecrop = "circlecrop"
    circleclose = "circleclose"
    circleopen = "circleopen"
    rectcrop = "rectcrop"
    diagtl = "diagtl"
    diagtr = "diagtr"
    diagbl = "diagbl"
    diagbr = "diagbr"
    radial = "radial"
    # Reveal
    horzopen = "horzopen"
    horzclose = "horzclose"
    vertopen = "vertopen"
    vertclose = "vertclose"
    revealleft = "revealleft"
    revealright = "revealright"
    revealup = "revealup"
    revealdown = "revealdown"
    # Cover
    coverleft = "coverleft"
    coverright = "coverright"
    coverup = "coverup"
    coverdown = "coverdown"
    # Stylized
    pixelize = "pixelize"
    zoomin = "zoomin"
    squeezeh = "squeezeh"
    squeezev = "squeezev"
    # Glitch
    hlwind = "hlwind"
    hrwind = "hrwind"
    vuwind = "vuwind"
    vdwind = "vdwind"
    hlslice = "hlslice"
    hrslice = "hrslice"
    vuslice = "vuslice"
    vdslice = "vdslice"


class Emotion(str, Enum):
    """Narration emotion tags."""
    neutral = "neutral"
    curious = "curious"
    confident = "confident"
    excited = "excited"
    surprised = "surprised"
    analytical = "analytical"
    impressed = "impressed"
    thoughtful = "thoughtful"
    serious = "serious"
    humorous = "humorous"
    skeptical = "skeptical"
    dramatic = "dramatic"


class TextPosition(str, Enum):
    """Text overlay position options."""
    center = "center"
    top = "top"
    bottom = "bottom"
    left = "left"
    right = "right"
    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class BRollDensity(str, Enum):
    """B-roll footage density."""
    low = "low"
    medium = "medium"
    high = "high"


class SocialPlatform(str, Enum):
    """Social card platform options."""
    reddit = "reddit"
    twitter = "twitter"
    hackernews = "hackernews"


# ── Data models for visual_instruction.data ────────────────────────────────

class StockWithTextData(BaseModel):
    """Data for stock_with_text scenes."""
    heading: str = ""
    body: str = ""
    keywords: list[str] = Field(default_factory=list, description="Pexels search keywords")
    position: TextPosition = TextPosition.center
    broll_density: BRollDensity = BRollDensity.low

class StockWithStatData(BaseModel):
    """Data for stock_with_stat scenes."""
    value: str = Field(description="The stat value to display, e.g. '22,000+'")
    label: str = ""
    subtitle: str = ""
    keywords: list[str] = Field(default_factory=list)

class StockQuoteData(BaseModel):
    """Data for stock_quote scenes."""
    quote: str = ""
    attribution: str = ""
    keywords: list[str] = Field(default_factory=list)

class SocialCardData(BaseModel):
    """Data for social_card scenes."""
    platform: SocialPlatform = SocialPlatform.reddit
    username: str = "u/anonymous"
    post_title: str = ""
    body: str = ""
    upvotes: int = 0
    comments: int = 0
    subreddit: str = ""
    keywords: list[str] = Field(default_factory=list)


class ChartSeries(BaseModel):
    """A named data series for multi-series charts."""
    name: str = ""
    values: list[float] = Field(default_factory=list)

class DataChartData(BaseModel):
    """Data for data_chart scenes — modern matplotlib-rendered charts.

    Two modes:
      1. **Static data** — provide `labels` + `values`/`series` directly.
      2. **Live Yahoo Finance** — provide `ticker`/`tickers` + `period` and
         the renderer fetches real-time price history automatically.
         No labels/values needed. Great for stock price charts.
    """
    chart_type: ChartType = ChartType.bar
    labels: list[str] = Field(default_factory=list, description="X-axis labels or category names")
    values: list[float] = Field(default=None, description="Single series values (use 'series' for multi-series)")
    series: list[ChartSeries] = Field(default=None, description="Multiple named series (for line/grouped_bar)")
    unit: str = Field(default="", description="Value unit: '$' for currency formatting, or empty")
    y_label: str = ""
    subtitle: str = ""
    source: str = Field(default="", description="Data source attribution shown bottom-left")
    duration: float = Field(default=None, description="Override scene duration in seconds")
    # Donut-specific
    center_value: str = Field(default="", description="Large text in donut center, e.g. '$60.9B'")
    center_label: str = Field(default="", description="Small text below center_value")
    # Yahoo Finance auto-fetch (leave values/series empty to use these)
    ticker: str = Field(default="", description="Single stock ticker for auto-fetch, e.g. 'NVDA'")
    tickers: list[str] = Field(default_factory=list, description="Multiple tickers for comparison chart, e.g. ['NVDA', 'AMD']")
    period: str = Field(default="1y", description="yfinance period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
    interval: str = Field(default="1wk", description="yfinance interval: 1d, 1wk, 1mo")
    value_type: str = Field(default="close", description="'close' for raw price, 'pct_change' for % indexed from start")


# ── Visual Instruction ─────────────────────────────────────────────────────

class VisualInstruction(BaseModel):
    """The visual_instruction block within each scene."""
    type: VisualType = Field(description="Scene visual type")
    title: str = Field(default="", description="Scene title / heading")
    transition: Transition = Transition.fade
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific data. See StockWithTextData, DataChartData, etc. for field details.",
    )


# ── Scene & Script ─────────────────────────────────────────────────────────

class SceneSchema(BaseModel):
    """A single scene in the video script."""
    scene_number: int = Field(description="1-based scene order")
    narration_text: str = Field(default="", description="Voiceover text for this scene")
    emotion: Emotion = Emotion.neutral
    visual_instruction: VisualInstruction


class VideoScriptSchema(BaseModel):
    """Top-level video script JSON structure.

    This is the schema for the JSON you import via the 'Import JSON' or
    'Paste JSON' buttons in the Script panel.
    """
    title: str = Field(description="Video title")
    scenes: list[SceneSchema] = Field(description="Ordered list of scenes")


# ── Reference response for the schema endpoint ────────────────────────────

class ScriptSchemaReference(BaseModel):
    """Schema reference response with all enum values listed."""
    visual_types: list[str] = Field(default_factory=lambda: [e.value for e in VisualType])
    chart_types: list[str] = Field(default_factory=lambda: [e.value for e in ChartType])
    transitions: list[str] = Field(default_factory=lambda: [e.value for e in Transition])
    emotions: list[str] = Field(default_factory=lambda: [e.value for e in Emotion])
    text_positions: list[str] = Field(default_factory=lambda: [e.value for e in TextPosition])
    broll_densities: list[str] = Field(default_factory=lambda: [e.value for e in BRollDensity])
    social_platforms: list[str] = Field(default_factory=lambda: [e.value for e in SocialPlatform])
    example_script: VideoScriptSchema = Field(
        default_factory=lambda: VideoScriptSchema(
            title="Example Finance Video",
            scenes=[
                SceneSchema(
                    scene_number=1,
                    narration_text="Welcome to our analysis.",
                    emotion=Emotion.confident,
                    visual_instruction=VisualInstruction(
                        type=VisualType.stock_with_text,
                        title="Hook",
                        transition=Transition.fade,
                        data={"heading": "Title Here", "body": "Subtitle", "keywords": ["finance", "chart"], "position": "center"},
                    ),
                ),
                SceneSchema(
                    scene_number=2,
                    narration_text="Let's look at the revenue numbers.",
                    emotion=Emotion.analytical,
                    visual_instruction=VisualInstruction(
                        type=VisualType.data_chart,
                        title="Revenue Comparison",
                        transition=Transition.smoothleft,
                        data={"chart_type": "bar", "labels": ["Company A", "Company B"], "values": [50000000, 30000000], "unit": "$", "source": "SEC Filings"},
                    ),
                ),
                SceneSchema(
                    scene_number=3,
                    narration_text="Now look at the stock performance over the past year.",
                    emotion=Emotion.excited,
                    visual_instruction=VisualInstruction(
                        type=VisualType.data_chart,
                        title="NVDA vs AMD Stock Performance",
                        transition=Transition.smoothright,
                        data={
                            "chart_type": "timeseries",
                            "tickers": ["NVDA", "AMD"],
                            "period": "1y",
                            "interval": "1wk",
                            "value_type": "pct_change",
                            "subtitle": "Percentage change indexed from 1 year ago",
                        },
                    ),
                ),
            ],
        )
    )
