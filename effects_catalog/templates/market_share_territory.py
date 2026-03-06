"""Market Share Territory Effect — area fills between competing timeseries.

Colors the territory each series "owns" above or below the other,
visualizing market share or performance dominance shifts over time.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "MarketShareTerritoryScene"


class InsufficientDataError(Exception):
    def __init__(self, count: int):
        self.count = count
        super().__init__(f"Need at least 2 series, got {count}")


def find_crossover_indices(values_a: list[float], values_b: list[float]) -> list[int]:
    """Find indices where series A and B cross over."""
    crossovers = []
    for i in range(1, min(len(values_a), len(values_b))):
        if (values_a[i - 1] >= values_b[i - 1]) != (values_a[i] >= values_b[i]):
            crossovers.append(i)
    return crossovers


def territory_owner(val_a: float, val_b: float) -> str:
    """Return 'a' if val_a >= val_b, else 'b'."""
    return "a" if val_a >= val_b else "b"


def generate(instruction: dict) -> str:
    """Generate Manim code for the Market Share Territory effect."""
    data = instruction.get("data", {})
    series = data.get("series", [])
    fill_opacity = data.get("fill_opacity", 0.3)
    title = instruction.get("title", "")

    # Extract names and colors from series
    series_a_name = series[0].get("name", "A") if len(series) > 0 else "A"
    series_b_name = series[1].get("name", "B") if len(series) > 1 else "B"
    color_a = series[0].get("territory_color", "#2962FF") if len(series) > 0 else "#2962FF"
    color_b = series[1].get("territory_color", "#EF4444") if len(series) > 1 else "#EF4444"

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Competing timeseries with territory fills."""

    def construct(self):
        self.camera.background_color = "#0F172A"

        series = {json.dumps(series)}
        fill_opacity = {json.dumps(fill_opacity)}
        title = {json.dumps(title)}

        if len(series) < 2:
            err = Text("Need at least 2 series", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        sa = series[0]
        sb = series[1]
        pts_a = sa.get("data", [])
        pts_b = sb.get("data", [])
        name_a = sa.get("name", "A")
        name_b = sb.get("name", "B")
        color_a = sa.get("territory_color", "#2962FF")
        color_b = sb.get("territory_color", "#EF4444")

        values_a = [p.get("value", 0) for p in pts_a]
        values_b = [p.get("value", 0) for p in pts_b]
        n = min(len(values_a), len(values_b))

        if n < 2:
            err = Text("Insufficient data", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        values_a = values_a[:n]
        values_b = values_b[:n]
        all_vals = values_a + values_b
        y_min = min(all_vals) * 0.92
        y_max = max(all_vals) * 1.08

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

        # Draw territory fills
        pts_a_scene = [axes.c2p(i, v) for i, v in enumerate(values_a)]
        pts_b_scene = [axes.c2p(i, v) for i, v in enumerate(values_b)]

        territory_fills = VGroup()
        for i in range(n - 1):
            top_a = values_a[i] >= values_b[i]
            color = color_a if top_a else color_b
            poly_pts = [
                pts_a_scene[i], pts_a_scene[i + 1],
                pts_b_scene[i + 1], pts_b_scene[i],
            ]
            poly = Polygon(
                *poly_pts,
                color=color, fill_color=color,
                fill_opacity=fill_opacity, stroke_width=0,
            )
            territory_fills.add(poly)

        self.play(FadeIn(territory_fills), run_time=0.5)

        # Draw lines on top
        line_a = VMobject(color=color_a, stroke_width=6)
        line_a.set_points_smoothly(pts_a_scene)
        line_b = VMobject(color=color_b, stroke_width=6)
        line_b.set_points_smoothly(pts_b_scene)

        self.play(Create(line_a), Create(line_b), run_time=1.5)

        # Legend
        legend_a = VGroup(
            Dot(radius=0.06, color=color_a),
            Text(name_a, font=FONT, font_size=18, color=color_a),
        ).arrange(RIGHT, buff=0.1)
        legend_b = VGroup(
            Dot(radius=0.06, color=color_b),
            Text(name_b, font=FONT, font_size=18, color=color_b),
        ).arrange(RIGHT, buff=0.1)
        legend = VGroup(legend_a, legend_b).arrange(RIGHT, buff=0.5)
        legend.to_edge(DOWN, buff=0.2)
        self.play(FadeIn(legend), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
