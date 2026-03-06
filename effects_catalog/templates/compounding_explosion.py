"""Compounding Explosion Effect — exponential growth with glow breakpoint.

Animates an exponential growth curve with a dramatic glow pulse where the
curve steepens beyond a threshold, visually conveying the moment compounding
"kicks in".
"""

from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger(__name__)

SCENE_CLASS = "CompoundingExplosionScene"


class RangeError(Exception):
    def __init__(self, value: float, field: str):
        self.value = value
        self.field = field
        super().__init__(f"{field} value {value} is invalid")


def compute_curve(principal: float, rate: float, years: int) -> list[float]:
    """Compute compound growth curve values."""
    return [principal * (1 + rate) ** y for y in range(years + 1)]


def find_breakpoint(values: list[float], threshold_ratio: float = 2.0) -> int:
    """Find the year where value exceeds threshold_ratio * principal."""
    if not values:
        return 0
    principal = values[0]
    for i, v in enumerate(values):
        if v >= principal * threshold_ratio:
            return i
    return len(values) - 1


def generate(instruction: dict) -> str:
    """Generate Manim code for the Compounding Explosion effect."""
    data = instruction.get("data", {})
    principal = data.get("principal", 10000)
    rate = data.get("rate", 0.10)
    years = data.get("years", 20)
    breakpoint_year = data.get("breakpoint_year", None)
    explosion_color = data.get("explosion_color", "#FFD700")
    line_color = data.get("line_color", "#FFFFFF")
    show_doubling_markers = data.get("show_doubling_markers", True)
    title = instruction.get("title", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"
import math

class {SCENE_CLASS}(MovingCameraScene):
    """Exponential growth curve with glow breakpoint."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        principal = {json.dumps(principal)}
        rate = {json.dumps(rate)}
        years = {json.dumps(years)}
        breakpoint_year = {json.dumps(breakpoint_year)}
        explosion_color = {json.dumps(explosion_color)}
        line_color = {json.dumps(line_color)}
        show_doubling_markers = {json.dumps(show_doubling_markers)}
        title = {json.dumps(title)}

        if rate <= 0 or years < 2:
            err = Text("Invalid parameters", font=FONT, font_size=28, color="#EF5350")
            self.play(FadeIn(err))
            self.wait(3)
            return

        # Compute curve
        curve_values = [principal * (1 + rate) ** y for y in range(years + 1)]

        # Auto-detect breakpoint if not specified
        if breakpoint_year is None:
            for i, v in enumerate(curve_values):
                if v >= principal * 2:
                    breakpoint_year = i
                    break
            if breakpoint_year is None:
                breakpoint_year = years // 2

        y_max = max(curve_values) * 1.1

        axes = Axes(
            x_range=[0, years, max(1, years // 5)],
            y_range=[0, y_max, y_max / 5],
            x_length=11, y_length=5.5,
            axis_config={{"color": "#9598A1", "stroke_width": 1.5}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        x_label = Text("Years", font=FONT, font_size=16, color="#787B86")
        x_label.next_to(axes.x_axis, DOWN, buff=0.15)

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#191919", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        self.play(Create(axes), FadeIn(x_label), run_time=0.4)

        # Draw curve progressively
        points = [axes.c2p(y, v) for y, v in enumerate(curve_values)]

        # Pre-breakpoint: normal line
        pre_points = points[:breakpoint_year + 1]
        if len(pre_points) >= 2:
            pre_line = VMobject(color=line_color, stroke_width=6)
            pre_line.set_points_smoothly(pre_points)
            self.play(Create(pre_line), run_time=1.0)

        # Breakpoint glow pulse
        if 0 < breakpoint_year < len(points):
            bp_dot = Dot(points[breakpoint_year], radius=0.1, color=explosion_color)
            glow = Circle(radius=0.1, color=explosion_color, stroke_width=3)
            glow.move_to(points[breakpoint_year])
            self.play(FadeIn(bp_dot), run_time=0.2)
            self.play(
                glow.animate.scale(8).set_stroke(opacity=0),
                Indicate(bp_dot, color=explosion_color, scale_factor=2),
                run_time=0.6,
            )
            self.remove(glow)

        # Post-breakpoint: glowing line
        post_points = points[breakpoint_year:]
        if len(post_points) >= 2:
            post_line = VMobject(color=explosion_color, stroke_width=3.5)
            post_line.set_points_smoothly(post_points)
            self.play(Create(post_line), run_time=1.0)

        # Doubling markers
        if show_doubling_markers:
            target = principal * 2
            for y, v in enumerate(curve_values):
                if v >= target:
                    marker = DashedLine(
                        axes.c2p(y, 0), axes.c2p(y, v),
                        color="#787B86", stroke_width=0.8, dash_length=0.1,
                    )
                    label = Text(f"2x", font=FONT, font_size=14, color="#787B86")
                    label.next_to(axes.c2p(y, 0), DOWN, buff=0.1)
                    self.play(Create(marker), FadeIn(label), run_time=0.2)
                    target *= 2

        # End badge
        badge = Text(
            f"${{curve_values[-1]:,.0f}}",
            font=FONT, font_size=18, color=explosion_color,
        )
        badge.next_to(axes.c2p(years, curve_values[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
