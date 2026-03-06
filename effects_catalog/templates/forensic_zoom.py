"""Forensic Zoom Effect — camera dive into a specific event date on a timeseries.

Displays a full-range timeseries chart, then zooms the camera into a narrow
window centered on the focus_date. Non-focus regions fade to blur_opacity,
and a SurroundingRectangle with glow_color highlights the target price action.

Supports two zoom modes:
  - "jump_cut" (default): instant camera transition after wide_hold
  - "travel": smooth camera pan from wide to focus
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "ForensicZoomScene"


class ForensicZoomError(Exception):
    """Base error for Forensic Zoom effect."""


class DateRangeError(ForensicZoomError):
    """Raised when focus_date falls outside the timeseries data range."""

    def __init__(self, focus_date: str, valid_start: str, valid_end: str):
        self.focus_date = focus_date
        self.valid_start = valid_start
        self.valid_end = valid_end
        super().__init__(
            f"focus_date '{focus_date}' is outside the data range "
            f"({valid_start} to {valid_end})"
        )


def generate(instruction: dict) -> str:
    """Generate Manim code for the Forensic Zoom effect.

    Expected instruction.data keys:
        focus_date: str — ISO date to zoom into
        focus_window_days: int — days around focus_date (default 30)
        glow_color: str — hex color for the glow rectangle (default "#FFD700")
        blur_opacity: float — opacity for non-focus regions (default 0.15)
        zoom_mode: str — "travel" or "jump_cut" (default "jump_cut")
        wide_hold: float — seconds to hold wide view before jump-cut (default 1.0)
        ticker/tickers/dates/series: timeseries data (enriched via Yahoo Finance)
    """
    data = instruction.get("data", {})
    focus_date = data.get("focus_date", "")
    focus_window_days = data.get("focus_window_days", 30)
    glow_color = data.get("glow_color", "#FFD700")
    blur_opacity = data.get("blur_opacity", 0.15)
    zoom_mode = data.get("zoom_mode", "jump_cut")
    wide_hold = data.get("wide_hold", 1.0)
    title = instruction.get("title", "")

    # Pass through timeseries data for the chart
    ticker = data.get("ticker", "")
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])
    events = data.get("events", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"
from datetime import datetime

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with forensic camera dive into a focus date."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"
        self.camera.frame.save_state()

        focus_date = {json.dumps(focus_date)}
        focus_window_days = {json.dumps(focus_window_days)}
        glow_color = {json.dumps(glow_color)}
        blur_opacity = {json.dumps(blur_opacity)}
        zoom_mode = {json.dumps(zoom_mode)}
        wide_hold = {json.dumps(wide_hold)}
        title = {json.dumps(title)}
        dates = {json.dumps(dates)}
        values = {json.dumps(values)}
        series = {json.dumps(series)}
        events = {json.dumps(events)}

        # Use first series if multi-series, or direct values
        if series and not values:
            s = series[0]
            dates = [p.get("date", "") for p in s.get("data", s.get("points", []))]
            values = [p.get("value", p.get("close", 0)) for p in s.get("data", s.get("points", []))]

        if len(dates) < 2 or len(values) < 2:
            err = Text("Insufficient data for forensic zoom", font=FONT, font_size=28, color="#EF5350")
            self.play(FadeIn(err))
            self.wait(3)
            return

        # Build axes
        n = len(values)
        y_min = min(values) * 0.95
        y_max = max(values) * 1.05

        axes = Axes(
            x_range=[0, n - 1, max(1, n // 6)],
            y_range=[y_min, y_max, (y_max - y_min) / 5],
            x_length=12, y_length=5.5,
            axis_config={{"color": "#9598A1", "stroke_width": 1.5}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        # Title
        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#191919", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        self.play(Create(axes), run_time=0.4)

        # Draw the price line
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="#2962FF", stroke_width=6)
        line.set_points_smoothly(points)
        self.play(Create(line), run_time=1.5)

        # Find focus index
        focus_idx = n // 2  # default to middle
        if focus_date and dates:
            for i, d in enumerate(dates):
                if d == focus_date or d.startswith(focus_date):
                    focus_idx = i
                    break

        # Calculate focus window bounds
        half_window = focus_window_days // 2
        focus_start = max(0, focus_idx - half_window)
        focus_end = min(n - 1, focus_idx + half_window)

        # Focus region center and width in scene coordinates
        focus_center_x = (axes.c2p(focus_start, 0)[0] + axes.c2p(focus_end, 0)[0]) / 2
        focus_width = abs(axes.c2p(focus_end, 0)[0] - axes.c2p(focus_start, 0)[0])
        focus_center_y = axes.c2p(0, (y_min + y_max) / 2)[1]

        # Wide view hold
        self.wait(wide_hold)

        # Fade non-focus regions
        left_cover = Rectangle(
            width=abs(axes.c2p(focus_start, 0)[0] - axes.get_left()[0]) + 0.5,
            height=6.5, color="#FFFFFF", fill_opacity=1 - blur_opacity,
            stroke_width=0,
        )
        left_cover.move_to([
            (axes.get_left()[0] + axes.c2p(focus_start, 0)[0]) / 2 - 0.25,
            axes.get_center()[1], 0
        ])

        right_cover = Rectangle(
            width=abs(axes.get_right()[0] - axes.c2p(focus_end, 0)[0]) + 0.5,
            height=6.5, color="#FFFFFF", fill_opacity=1 - blur_opacity,
            stroke_width=0,
        )
        right_cover.move_to([
            (axes.c2p(focus_end, 0)[0] + axes.get_right()[0]) / 2 + 0.25,
            axes.get_center()[1], 0
        ])

        # Camera zoom
        zoom_width = max(focus_width * 1.5, 4)
        zoom_target = [focus_center_x, focus_center_y, 0]

        if zoom_mode == "travel":
            self.play(
                FadeIn(left_cover), FadeIn(right_cover),
                self.camera.frame.animate.set(width=zoom_width).move_to(zoom_target),
                run_time=2.0,
            )
        else:
            # jump_cut: instant transition
            self.play(FadeIn(left_cover), FadeIn(right_cover), run_time=0.3)
            self.camera.frame.set(width=zoom_width).move_to(zoom_target)

        # Glow rectangle around focus region
        focus_vals = values[focus_start:focus_end + 1]
        if focus_vals:
            fy_min = min(focus_vals)
            fy_max = max(focus_vals)
            glow_rect = SurroundingRectangle(
                VGroup(
                    Dot(axes.c2p(focus_start, fy_min), radius=0.01),
                    Dot(axes.c2p(focus_end, fy_max), radius=0.01),
                ),
                color=glow_color, buff=0.15,
                stroke_width=6, fill_opacity=0.05,
            )
            self.play(Create(glow_rect), run_time=0.4)
            self.play(Indicate(glow_rect, color=glow_color, scale_factor=1.02), run_time=0.5)

        # Event markers in focus window
        for evt in events:
            evt_date = evt.get("date", "")
            evt_label = evt.get("label", "")
            for i, d in enumerate(dates):
                if d == evt_date or d.startswith(evt_date):
                    if focus_start <= i <= focus_end:
                        marker = DashedLine(
                            axes.c2p(i, y_min), axes.c2p(i, y_max),
                            color="#FFD60A", stroke_width=1, dash_length=0.1,
                        )
                        label = Text(evt_label, font_size=12, color="#FFD60A")
                        label.next_to(axes.c2p(i, y_max), UP, buff=0.1)
                        self.play(Create(marker), FadeIn(label), run_time=0.3)
                    break

        self.wait(3)
        self.play(Restore(self.camera.frame), run_time=0.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
