"""Speed Ramp Effect — variable playback speed across time segments.

Fast-forwards boring decades and plays critical crash periods in slow motion
by varying the line-draw animation speed across configurable segments.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "SpeedRampScene"


class DateOrderError(Exception):
    def __init__(self, start: str, end: str):
        self.start = start
        self.end = end
        super().__init__(f"Speed regime start '{start}' is after end '{end}'")


class RangeError(Exception):
    def __init__(self, speed: float):
        self.speed = speed
        super().__init__(f"Speed value {speed} must be > 0")


def compute_segment_durations(
    n_points: int,
    speed_regimes: list[dict],
    dates: list[str],
    base_duration: float = 2.0,
    transition_frames: int = 10,
) -> list[float]:
    """Compute per-segment draw durations based on speed regimes."""
    durations = [base_duration / max(n_points - 1, 1)] * max(n_points - 1, 0)
    # Apply speed multipliers
    for regime in speed_regimes:
        r_start = regime.get("start", "")
        r_end = regime.get("end", "")
        speed = regime.get("speed", 1.0)
        if speed <= 0:
            continue
        for i in range(len(durations)):
            if i < len(dates) and dates[i] >= r_start and dates[i] <= r_end:
                durations[i] = durations[i] / speed
    return durations


def generate(instruction: dict) -> str:
    """Generate Manim code for the Speed Ramp effect."""
    data = instruction.get("data", {})
    speed_regimes = data.get("speed_regimes", [])
    transition_frames = data.get("transition_frames", 10)
    title = instruction.get("title", "")
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Timeseries with variable-speed line drawing."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        speed_regimes = {json.dumps(speed_regimes)}
        transition_frames = {json.dumps(transition_frames)}
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

        self.play(Create(axes), run_time=0.4)

        # Compute per-segment speed
        base_dur = 2.0 / (n - 1)
        seg_durations = [base_dur] * (n - 1)
        for regime in speed_regimes:
            r_start = regime.get("start", "")
            r_end = regime.get("end", "")
            speed = regime.get("speed", 1.0)
            if speed <= 0:
                speed = 1.0
            for i in range(n - 1):
                if i < len(dates) and dates[i] >= r_start and dates[i] <= r_end:
                    seg_durations[i] = base_dur / speed

        # Draw segments with varying speed
        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        for i in range(n - 1):
            seg = Line(points[i], points[i + 1], color="#2962FF", stroke_width=6)
            self.play(Create(seg), run_time=max(seg_durations[i], 0.02))

        # End badge
        badge = Text(f"${{values[-1]:,.0f}}", font=FONT, font_size=18, color="#191919")
        badge.next_to(axes.c2p(n - 1, values[-1]), RIGHT, buff=0.15)
        self.play(FadeIn(badge), run_time=0.3)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
