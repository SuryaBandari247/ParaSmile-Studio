"""Liquidity Shock — dispatcher that routes to simple or terminal variant.

Two versions:
  - **simple** (default): White-background line chart with flash line, shock dot,
    camera shake. Clean and fast — good for quick explainers.
  - **terminal**: TradingView dark-theme candlestick chart with volume bars,
    SMAs, Bollinger Bands, OHLC header. Full terminal look — good for deep dives.

Select variant via ``data.variant`` in the instruction dict:
    {"data": {"variant": "simple", ...}}   # default
    {"data": {"variant": "terminal", ...}}
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Default scene class — overridden by the chosen variant
SCENE_CLASS = "LiquidityShockSimpleScene"


def generate(instruction: dict) -> str:
    """Dispatch to the correct liquidity_shock variant."""
    data = instruction.get("data", {})
    variant = data.get("variant", "simple").lower().strip()

    if variant == "terminal":
        from effects_catalog.templates.liquidity_shock_terminal import generate as _gen
        return _gen(instruction)
    else:
        from effects_catalog.templates.liquidity_shock_simple import generate as _gen
        return _gen(instruction)


def render(instruction: dict, output_path: str | None = None) -> str:
    """Dispatch render to the correct variant.

    For terminal: calls Puppeteer pipeline directly, returns video path.
    For simple: falls back to generate() (caller must handle Manim rendering).
    """
    data = instruction.get("data", {})
    variant = data.get("variant", "simple").lower().strip()

    if variant == "terminal":
        from effects_catalog.templates.liquidity_shock_terminal import render as _render
        return _render(instruction, output_path)
    else:
        raise NotImplementedError(
            "Simple variant uses Manim codegen — call generate() and render externally."
        )
