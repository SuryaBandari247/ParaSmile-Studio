"""Momentum Glow Effect — dynamic glow on timeseries based on rolling slope.

Makes high-momentum periods visually "hot" with a neon trail and cooling
periods fade back to a neutral baseline.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "MomentumGlowScene"


class InsufficientDataError(Exception):
    def __init__(self, count: int, window: int):
        self.count = count
        self.window = window
        super().__init__(
            f"Need at least {window} data points for momentum_window, got {count}"
        )


def compute_rolling_slope(values: list[float], window: int) -> list[float]:
    """Compute rolling slope over a window. Returns list of slopes (len = len(values))."""
    slopes = [0.0] * len(values)
    for i in range(window, len(values)):
        segment = values[i - window:i + 1]
        slope = (segment[-1] - segment[0]) / window
        slopes[i] = slope
    return slopes


def generate(instruction: dict) -> str:
    """Generate Manim code for the Momentum Glow effect."""
    data = instruction.get("data", {})
    momentum_window = data.get("momentum_window", 20)
    glow_color_up = data.get("glow_color_up", "#00FFAA")
    glow_color_down = data.get("glow_color_down", "#FF453A")
    glow_intensity = data.get("glow_intensity", 0.8)
    glow_threshold_sigma = data.get("glow_threshold_sigma", 1.0)
    title = instruction.get("title", "")
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with momentum-based glow intensity."""

    def construct(self):
        self.camera.background_color = "#0F172A"

        momentum_window = {json.dumps(momentum_window)}
        glow_color_up = {json.dumps(glow_color_up)}
        glow_color_down = {json.dumps(glow_color_down)}
        glow_intensity = {json.dumps(glow_intensity)}
        glow_threshold_sigma = {json.dumps(glow_threshold_sigma)}
        title = {json.dumps(title)}
        dates = {json.dumps(dates)}
        values = {json.dumps(values)}
        series = {json.dumps(series)}

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

        self.play(Create(axes), run_time=0.4)

        # Compute rolling slopes
        slopes = [0.0] * n
        for i in range(momentum_window, n):
            slopes[i] = (values[i] - values[i - momentum_window]) / momentum_window

        abs_slopes = [abs(s) for s in slopes if s != 0]
        mean_slope = np.mean(abs_slopes) if abs_slopes else 0
        std_slope = np.std(abs_slopes) if abs_slopes else 1
        threshold = mean_slope + glow_threshold_sigma * std_slope

        # Draw segments with varying glow
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        segments = VGroup()
        for i in range(n - 1):
            seg = Line(points[i], points[i + 1], stroke_width=6)
            slope = slopes[i + 1]
            if abs(slope) > threshold:
                color = glow_color_up if slope > 0 else glow_color_down
                seg.set_stroke(color=color, width=4, opacity=glow_intensity)
            else:
                seg.set_stroke(color="#2962FF", width=2, opacity=0.7)
            segments.add(seg)

        self.play(LaggedStart(*[Create(s) for s in segments], lag_ratio=0.02), run_time=2.0)

        # End badge
        badge = Text(f"${{values[-1]:,.0f}}", font=FONT, font_size=18, color="#F8FAFC")
        badge.next_to(axes.c2p(n - 1, values[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
