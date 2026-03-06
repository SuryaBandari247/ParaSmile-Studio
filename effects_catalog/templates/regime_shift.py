"""Regime Shift Effect — color-coded background zones for economic eras.

Renders labeled background zones on a timeseries chart to delineate
economic eras (e.g., QE Era, Rate Hikes), providing temporal context.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "RegimeShiftScene"


class DateOrderError(Exception):
    def __init__(self, start: str, end: str):
        self.start = start
        self.end = end
        super().__init__(f"Regime start '{start}' is after end '{end}'")


class DateRangeError(Exception):
    def __init__(self, regime_label: str, data_start: str, data_end: str):
        self.regime_label = regime_label
        self.data_start = data_start
        self.data_end = data_end
        super().__init__(
            f"Regime '{regime_label}' is outside data range ({data_start} to {data_end})"
        )


def generate(instruction: dict) -> str:
    """Generate Manim code for the Regime Shift effect."""
    data = instruction.get("data", {})
    regimes = data.get("regimes", [])
    zone_opacity = data.get("zone_opacity", 0.15)
    title = instruction.get("title", "")
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with color-coded regime background zones."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        regimes = {json.dumps(regimes)}
        zone_opacity = {json.dumps(zone_opacity)}
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
            err = Text("Insufficient data", font=FONT, font_size=28, color="#EF5350")
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
            axis_config={{"color": "#9598A1", "stroke_width": 1.5}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#191919", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        # Draw regime zones first (behind the line)
        zone_group = VGroup()
        for regime in regimes:
            r_start = regime.get("start", "")
            r_end = regime.get("end", "")
            r_label = regime.get("label", "")
            r_color = regime.get("color", "#787B86")

            start_idx = 0
            end_idx = n - 1
            for i, d in enumerate(dates):
                if d >= r_start and start_idx == 0:
                    start_idx = i
                if d <= r_end:
                    end_idx = i

            x_left = axes.c2p(start_idx, 0)[0]
            x_right = axes.c2p(end_idx, 0)[0]
            zone_width = abs(x_right - x_left)
            zone_height = abs(axes.c2p(0, y_max)[1] - axes.c2p(0, y_min)[1])

            zone = Rectangle(
                width=zone_width, height=zone_height,
                color=r_color, fill_color=r_color,
                fill_opacity=zone_opacity, stroke_width=0,
            )
            zone.move_to([(x_left + x_right) / 2, axes.get_center()[1], 0])

            label = Text(r_label, font=FONT, font_size=14, color=r_color)
            label.move_to(zone.get_top() + UP * 0.15)

            zone_group.add(VGroup(zone, label))

        self.play(Create(axes), run_time=0.4)

        # Sequential zone reveal
        for zg in zone_group:
            self.play(FadeIn(zg), run_time=0.3)

        # Draw price line on top
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="#2962FF", stroke_width=6)
        line.set_points_smoothly(points)
        self.play(Create(line), run_time=1.5)

        # End badge
        badge = Text(f"${{values[-1]:,.0f}}", font=FONT, font_size=18, color="#191919")
        badge.next_to(axes.c2p(n - 1, values[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
