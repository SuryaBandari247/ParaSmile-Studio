"""Relative Velocity Comparison Effect — dynamic arrow between two timeseries.

Renders dual timeseries with a dynamic Arrow between series and a
DecimalNumber for percentage spread, continuously tracking the rightmost
drawn data point.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "RelativeVelocityScene"


def compute_overlap(dates_a: list[str], dates_b: list[str]) -> list[str]:
    """Return the sorted intersection of two date lists."""
    overlap = sorted(set(dates_a) & set(dates_b))
    return overlap


def compute_spread(val_a: float, val_b: float) -> float:
    """Compute percentage spread between two values."""
    base = min(abs(val_a), abs(val_b))
    if base == 0:
        return 0.0
    return abs(val_a - val_b) / base * 100


def generate(instruction: dict) -> str:
    """Generate Manim code for the Relative Velocity effect."""
    data = instruction.get("data", {})
    series_a_name = data.get("series_a_name", "Series A")
    series_b_name = data.get("series_b_name", "Series B")
    show_delta_arrow = data.get("show_delta_arrow", True)
    delta_format = data.get("delta_format", "+{:.0f}% Lead")
    arrow_color = data.get("arrow_color", "#F8FAFC")
    title = instruction.get("title", "")

    series = data.get("series", [])
    dates = data.get("dates", [])
    values_a = data.get("values_a", [])
    values_b = data.get("values_b", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Dual timeseries with dynamic delta arrow."""

    def construct(self):
        self.camera.background_color = "#0F172A"

        series_a_name = {json.dumps(series_a_name)}
        series_b_name = {json.dumps(series_b_name)}
        show_delta_arrow = {json.dumps(show_delta_arrow)}
        delta_format = {json.dumps(delta_format)}
        arrow_color = {json.dumps(arrow_color)}
        title = {json.dumps(title)}
        series = {json.dumps(series)}
        dates = {json.dumps(dates)}
        values_a = {json.dumps(values_a)}
        values_b = {json.dumps(values_b)}

        # Extract from series if provided
        if series and len(series) >= 2 and not values_a:
            sa = series[0]
            sb = series[1]
            pts_a = sa.get("data", sa.get("points", []))
            pts_b = sb.get("data", sb.get("points", []))
            dates_a = [p.get("date", "") for p in pts_a]
            dates_b = [p.get("date", "") for p in pts_b]
            vals_a_map = {{p.get("date", ""): p.get("value", p.get("close", 0)) for p in pts_a}}
            vals_b_map = {{p.get("date", ""): p.get("value", p.get("close", 0)) for p in pts_b}}
            overlap = sorted(set(dates_a) & set(dates_b))
            if overlap:
                dates = overlap
                values_a = [vals_a_map[d] for d in overlap]
                values_b = [vals_b_map[d] for d in overlap]
            series_a_name = sa.get("name", series_a_name)
            series_b_name = sb.get("name", series_b_name)

        if len(values_a) < 2 or len(values_b) < 2:
            err = Text("Insufficient data for comparison", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        n = min(len(values_a), len(values_b))
        values_a = values_a[:n]
        values_b = values_b[:n]

        all_vals = values_a + values_b
        y_min = min(all_vals) * 0.92
        y_max = max(all_vals) * 1.08

        axes = Axes(
            x_range=[0, n - 1, max(1, n // 6)],
            y_range=[y_min, y_max, (y_max - y_min) / 5],
            x_length=11, y_length=5.5,
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

        # Draw both lines
        color_a = "#2962FF"
        color_b = "#EF4444"

        pts_a = [axes.c2p(i, v) for i, v in enumerate(values_a)]
        pts_b = [axes.c2p(i, v) for i, v in enumerate(values_b)]

        line_a = VMobject(color=color_a, stroke_width=6)
        line_a.set_points_smoothly(pts_a)
        line_b = VMobject(color=color_b, stroke_width=6)
        line_b.set_points_smoothly(pts_b)

        self.play(Create(line_a), Create(line_b), run_time=1.5)

        # Legend
        legend_a = VGroup(
            Dot(radius=0.06, color=color_a),
            Text(series_a_name, font=FONT, font_size=18, color=color_a),
        ).arrange(RIGHT, buff=0.1)
        legend_b = VGroup(
            Dot(radius=0.06, color=color_b),
            Text(series_b_name, font=FONT, font_size=18, color=color_b),
        ).arrange(RIGHT, buff=0.1)
        legend = VGroup(legend_a, legend_b).arrange(RIGHT, buff=0.5)
        legend.to_edge(UP, buff=0.55 if title else 0.2)
        self.play(FadeIn(legend), run_time=0.3)

        # Delta arrow at the last point
        if show_delta_arrow and n > 0:
            last_a = values_a[-1]
            last_b = values_b[-1]
            top_val = max(last_a, last_b)
            bot_val = min(last_a, last_b)

            arrow = Arrow(
                axes.c2p(n - 1, bot_val),
                axes.c2p(n - 1, top_val),
                color=arrow_color, stroke_width=2, buff=0.05,
            )
            self.play(Create(arrow), run_time=0.3)

            base = min(abs(last_a), abs(last_b))
            spread = abs(last_a - last_b) / base * 100 if base > 0 else 0
            leader = series_a_name if last_a > last_b else series_b_name
            spread_text = Text(
                f"{{spread:.0f}}% gap",
                font=FONT, font_size=18, color=arrow_color,
            )
            spread_text.next_to(arrow, RIGHT, buff=0.15)
            self.play(FadeIn(spread_text), run_time=0.3)

        # End-of-line badges
        badge_a = Text(f"${{values_a[-1]:,.0f}}", font=FONT, font_size=18, color=color_a)
        badge_a.next_to(axes.c2p(n - 1, values_a[-1]), RIGHT, buff=0.15)
        badge_b = Text(f"${{values_b[-1]:,.0f}}", font=FONT, font_size=18, color=color_b)
        badge_b.next_to(axes.c2p(n - 1, values_b[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge_a), FadeIn(badge_b), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
