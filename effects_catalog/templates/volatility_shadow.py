"""Volatility Shadow Effect — drawdown "Pain Zone" visualization.

Overlays a semi-transparent area fill on timeseries charts during drawdown
periods, visualizing the distance between the running all-time high and the
current price. The shadow dynamically grows and shrinks as the line animates.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "VolatilityShadowScene"


class InsufficientDataError(Exception):
    """Raised when timeseries has fewer than 2 data points."""

    def __init__(self, count: int):
        self.count = count
        super().__init__(
            f"Volatility shadow requires at least 2 data points, got {count}"
        )


def compute_drawdown_regions(values: list[float]) -> list[dict]:
    """Compute drawdown regions from a price series.

    Returns a list of dicts with:
        start_idx, end_idx: indices of the drawdown region
        max_drawdown_pct: peak drawdown percentage in this region
        running_max_at_start: the ATH value when drawdown began
    """
    if len(values) < 2:
        return []

    regions: list[dict] = []
    running_max = values[0]
    in_drawdown = False
    region_start = 0
    peak_dd = 0.0
    rm_at_start = running_max

    for i, v in enumerate(values):
        if v >= running_max:
            running_max = v
            if in_drawdown:
                regions.append({
                    "start_idx": region_start,
                    "end_idx": i - 1,
                    "max_drawdown_pct": peak_dd,
                    "running_max_at_start": rm_at_start,
                })
                in_drawdown = False
                peak_dd = 0.0
        else:
            dd_pct = (running_max - v) / running_max * 100 if running_max > 0 else 0
            if not in_drawdown:
                in_drawdown = True
                region_start = i
                rm_at_start = running_max
            peak_dd = max(peak_dd, dd_pct)

    if in_drawdown:
        regions.append({
            "start_idx": region_start,
            "end_idx": len(values) - 1,
            "max_drawdown_pct": peak_dd,
            "running_max_at_start": rm_at_start,
        })

    return regions


def generate(instruction: dict) -> str:
    """Generate Manim code for the Volatility Shadow effect."""
    data = instruction.get("data", {})
    shadow_color = data.get("shadow_color", "#FF453A")
    shadow_opacity = data.get("shadow_opacity", 0.2)
    show_drawdown_pct = data.get("show_drawdown_pct", False)
    title = instruction.get("title", "")

    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])
    events = data.get("events", [])
    ticker = data.get("ticker", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with drawdown shadow overlay."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        shadow_color = {json.dumps(shadow_color)}
        shadow_opacity = {json.dumps(shadow_opacity)}
        show_drawdown_pct = {json.dumps(show_drawdown_pct)}
        title = {json.dumps(title)}
        dates = {json.dumps(dates)}
        values = {json.dumps(values)}
        series = {json.dumps(series)}
        events = {json.dumps(events)}

        # Use first series if multi-series
        if series and not values:
            s = series[0]
            pts = s.get("data", s.get("points", []))
            dates = [p.get("date", "") for p in pts]
            values = [p.get("value", p.get("close", 0)) for p in pts]

        if len(values) < 2:
            err = Text("Insufficient data for volatility shadow", font=FONT, font_size=28, color="#EF4444")
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
            axis_config={{"color": "#9CA3AF", "stroke_width": 1.5}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#111827", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        self.play(Create(axes), run_time=0.4)

        # Compute running max and drawdown regions
        running_max = []
        rm = values[0]
        for v in values:
            rm = max(rm, v)
            running_max.append(rm)

        # Draw price line progressively
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="#2563EB", stroke_width=6)
        line.set_points_smoothly(points)

        # Draw running max line (faint)
        rm_points = [axes.c2p(i, rm) for i, rm in enumerate(running_max)]
        rm_line = VMobject(color="#9CA3AF", stroke_width=1, stroke_opacity=0.5)
        rm_line.set_points_smoothly(rm_points)

        self.play(Create(rm_line), run_time=0.6)
        self.play(Create(line), run_time=1.5)

        # Build shadow polygons for drawdown regions
        shadows = VGroup()
        drawdown_labels = VGroup()

        in_dd = False
        dd_start = 0
        peak_dd_pct = 0.0

        for i in range(n):
            if values[i] < running_max[i]:
                if not in_dd:
                    in_dd = True
                    dd_start = i
                    peak_dd_pct = 0.0
                dd_pct = (running_max[i] - values[i]) / running_max[i] * 100 if running_max[i] > 0 else 0
                peak_dd_pct = max(peak_dd_pct, dd_pct)
            else:
                if in_dd:
                    # Build polygon for this drawdown region
                    poly_points = []
                    for j in range(dd_start, i + 1):
                        poly_points.append(axes.c2p(j, running_max[j]))
                    for j in range(i, dd_start - 1, -1):
                        poly_points.append(axes.c2p(j, values[j]))
                    if len(poly_points) >= 3:
                        shadow = Polygon(
                            *poly_points,
                            color=shadow_color,
                            fill_color=shadow_color,
                            fill_opacity=shadow_opacity,
                            stroke_width=0,
                        )
                        shadows.add(shadow)

                        if show_drawdown_pct and peak_dd_pct >= 1.0:
                            mid_idx = (dd_start + i) // 2
                            mid_val = (running_max[mid_idx] + values[mid_idx]) / 2
                            label = Text(
                                f"-{{peak_dd_pct:.1f}}%",
                                font=FONT, font_size=18, color=shadow_color,
                            )
                            label.move_to(axes.c2p(mid_idx, mid_val))
                            drawdown_labels.add(label)

                    in_dd = False

        # Handle trailing drawdown
        if in_dd:
            poly_points = []
            for j in range(dd_start, n):
                poly_points.append(axes.c2p(j, running_max[j]))
            for j in range(n - 1, dd_start - 1, -1):
                poly_points.append(axes.c2p(j, values[j]))
            if len(poly_points) >= 3:
                shadow = Polygon(
                    *poly_points,
                    color=shadow_color,
                    fill_color=shadow_color,
                    fill_opacity=shadow_opacity,
                    stroke_width=0,
                )
                shadows.add(shadow)

                if show_drawdown_pct and peak_dd_pct >= 1.0:
                    mid_idx = (dd_start + n - 1) // 2
                    mid_val = (running_max[mid_idx] + values[mid_idx]) / 2
                    label = Text(
                        f"-{{peak_dd_pct:.1f}}%",
                        font=FONT, font_size=18, color=shadow_color,
                    )
                    label.move_to(axes.c2p(mid_idx, mid_val))
                    drawdown_labels.add(label)

        if shadows:
            self.play(
                LaggedStart(*[FadeIn(s) for s in shadows], lag_ratio=0.2),
                run_time=max(0.5, len(shadows) * 0.3),
            )

        if drawdown_labels:
            self.play(
                LaggedStart(*[FadeIn(l) for l in drawdown_labels], lag_ratio=0.15),
                run_time=0.5,
            )

        # End-of-line value badge
        if values:
            last_val = values[-1]
            badge = Text(f"${{last_val:,.0f}}", font=FONT, font_size=18, color="#2563EB")
            badge.next_to(axes.c2p(n - 1, last_val), RIGHT, buff=0.15)
            self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
