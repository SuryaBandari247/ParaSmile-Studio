"""Contextual Heatmap Effect — benchmark-driven background color gradient.

Overlays a green-to-red background color gradient on timeseries charts
based on a benchmark index's performance, providing macroeconomic context
for stock price movements.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "ContextualHeatmapScene"


class TickerResolutionError(Exception):
    """Raised when benchmark_ticker fails to resolve."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"Failed to resolve benchmark ticker: {ticker}")


def assign_heatmap_color(
    benchmark_value: float, benchmark_start: float,
    green_color: str, red_color: str,
) -> str:
    """Return green or red color based on benchmark vs its start value."""
    return green_color if benchmark_value >= benchmark_start else red_color


def generate(instruction: dict) -> str:
    """Generate Manim code for the Contextual Heatmap effect."""
    data = instruction.get("data", {})
    benchmark_ticker = data.get("benchmark_ticker", "^GSPC")
    green_color = data.get("green_color", "#00E676")
    red_color = data.get("red_color", "#FF453A")
    heatmap_opacity = data.get("heatmap_opacity", 0.15)
    benchmark_label = data.get("benchmark_label", "S&P 500")
    title = instruction.get("title", "")

    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])
    benchmark_values = data.get("benchmark_values", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with benchmark-driven background heatmap."""

    def construct(self):
        self.camera.background_color = "#0F172A"

        green_color = {json.dumps(green_color)}
        red_color = {json.dumps(red_color)}
        heatmap_opacity = {json.dumps(heatmap_opacity)}
        benchmark_label = {json.dumps(benchmark_label)}
        title = {json.dumps(title)}
        dates = {json.dumps(dates)}
        values = {json.dumps(values)}
        series = {json.dumps(series)}
        benchmark_values = {json.dumps(benchmark_values)}

        if series and not values:
            s = series[0]
            pts = s.get("data", s.get("points", []))
            dates = [p.get("date", "") for p in pts]
            values = [p.get("value", p.get("close", 0)) for p in pts]

        if len(values) < 2:
            err = Text("Insufficient data", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        n = len(values)
        y_min = min(values) * 0.92
        y_max = max(values) * 1.08

        axes = Axes(
            x_range=[0, n - 1, max(1, n // 6)],
            y_range=[y_min, y_max, (y_max - y_min) / 5],
            x_length=12, y_length=5.5,
            axis_config={{"color": "#334155", "stroke_width": 1.5}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#F8FAFC", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        # Heatmap background strips
        if benchmark_values and len(benchmark_values) >= n:
            bm_start = benchmark_values[0]
            strips = VGroup()
            strip_w = axes.x_length / n
            for i in range(n):
                color = green_color if benchmark_values[i] >= bm_start else red_color
                strip = Rectangle(
                    width=strip_w, height=axes.y_length,
                    color=color, fill_color=color,
                    fill_opacity=heatmap_opacity, stroke_width=0,
                )
                strip.move_to(axes.c2p(i, (y_min + y_max) / 2))
                strips.add(strip)
            self.play(FadeIn(strips), run_time=0.5)

            # Benchmark label
            bm_label = Text(
                f"Background: {{benchmark_label}}",
                font=FONT, font_size=16, color="#64748B",
            )
            bm_label.to_edge(DOWN, buff=0.15).to_edge(LEFT, buff=0.3)
            self.play(FadeIn(bm_label), run_time=0.2)

        self.play(Create(axes), run_time=0.4)

        # Draw price line
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="#2962FF", stroke_width=6)
        line.set_points_smoothly(points)
        self.play(Create(line), run_time=1.5)

        # End badge
        badge = Text(f"${{values[-1]:,.0f}}", font=FONT, font_size=18, color="#2962FF")
        badge.next_to(axes.c2p(n - 1, values[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
