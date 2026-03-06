"""Historical Rank Effect — vertical percentile ladder with animated marker.

Shows where a current value sits within its historical distribution,
with labeled percentile bands and an animated marker settling into position.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "HistoricalRankScene"


class InsufficientDataError(Exception):
    def __init__(self, count: int):
        self.count = count
        super().__init__(f"Need at least 10 historical values, got {count}")


def compute_percentile(current: float, historical: list[float]) -> float:
    """Compute percentile rank of current value within historical values."""
    if not historical:
        return 0.0
    count_below = sum(1 for v in historical if v < current)
    return (count_below / len(historical)) * 100


DEFAULT_BANDS = [
    {"label": "Cheap", "pct": 25},
    {"label": "Normal", "pct": 50},
    {"label": "Expensive", "pct": 75},
    {"label": "Extreme", "pct": 95},
]


def generate(instruction: dict) -> str:
    """Generate Manim code for the Historical Rank effect."""
    data = instruction.get("data", {})
    current_value = data.get("current_value", 0)
    historical_values = data.get("historical_values", [])
    metric_label = data.get("metric_label", "Value")
    percentile_bands = data.get("percentile_bands", DEFAULT_BANDS)
    title = instruction.get("title", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(Scene):
    """Vertical percentile ladder with animated marker."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        current_value = {json.dumps(current_value)}
        historical_values = {json.dumps(historical_values)}
        metric_label = {json.dumps(metric_label)}
        percentile_bands = {json.dumps(percentile_bands)}
        title = {json.dumps(title)}

        if len(historical_values) < 10:
            err = Text("Insufficient historical data", font=FONT, font_size=28, color="#EF5350")
            self.play(FadeIn(err))
            self.wait(3)
            return

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#191919", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        # Compute percentile
        count_below = sum(1 for v in historical_values if v < current_value)
        percentile = (count_below / len(historical_values)) * 100

        # Draw vertical ladder
        ladder_height = 5.0
        ladder_x = -1.0
        ladder_bottom = DOWN * 2.5
        ladder_top = ladder_bottom + UP * ladder_height

        # Main vertical bar
        bar = Line(ladder_bottom, ladder_top, color="#9598A1", stroke_width=3)
        self.play(Create(bar), run_time=0.4)

        # Percentile bands
        band_colors = ["#26A69A", "#2962FF", "#f0883e", "#EF5350"]
        prev_pct = 0
        for i, band in enumerate(percentile_bands):
            pct = band.get("pct", 50)
            label_text = band.get("label", "")
            color = band_colors[i % len(band_colors)]

            y_start = ladder_bottom + UP * (prev_pct / 100 * ladder_height)
            y_end = ladder_bottom + UP * (pct / 100 * ladder_height)

            zone = Rectangle(
                width=1.5, height=abs(y_end[1] - y_start[1]),
                color=color, fill_color=color, fill_opacity=0.15,
                stroke_width=0.5,
            )
            zone.move_to([(ladder_x + 0.75), (y_start[1] + y_end[1]) / 2, 0])

            label = Text(label_text, font=FONT, font_size=14, color=color)
            label.next_to(zone, RIGHT, buff=0.2)

            pct_label = Text(f"{{pct}}th", font=FONT, font_size=14, color="#787B86")
            pct_label.move_to([ladder_x - 0.5, y_end[1], 0])

            self.play(FadeIn(zone), FadeIn(label), FadeIn(pct_label), run_time=0.2)
            prev_pct = pct

        # Animated marker settling into position
        marker_y = ladder_bottom + UP * (percentile / 100 * ladder_height)
        marker = Triangle(color="#FFD60A", fill_color="#FFD60A", fill_opacity=1)
        marker.scale(0.15)
        marker.rotate(-PI / 2)
        marker.move_to([ladder_x - 0.3, ladder_top[1], 0])

        self.play(FadeIn(marker), run_time=0.2)
        self.play(marker.animate.move_to([ladder_x - 0.3, marker_y[1], 0]), run_time=1.0)

        # Value and percentile label
        value_text = Text(
            f"{{metric_label}}: {{current_value}} ({{percentile:.0f}}th percentile)",
            font_size=16, color="#FFD60A",
        )
        value_text.next_to(marker, LEFT, buff=0.3)
        self.play(FadeIn(value_text), run_time=0.3)
        self.play(Indicate(marker, color="#FFD60A", scale_factor=1.3), run_time=0.5)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
