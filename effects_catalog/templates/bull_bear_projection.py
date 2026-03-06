"""Bull vs Bear Projection Effect — three-path future projection from today.

Draws historical price line up to "Today", then fans out three dashed
projection lines (Optimistic, Realistic, Pessimistic) using configurable
compound growth rates.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "BullBearProjectionScene"


class InsufficientDataError(Exception):
    def __init__(self, count: int):
        self.count = count
        super().__init__(f"Bull/Bear projection requires at least 2 data points, got {count}")


def compute_projection(last_price: float, rate: float, years: int) -> list[float]:
    """Compute compound growth projection. Returns list of yearly values."""
    return [last_price * (1 + rate) ** y for y in range(years + 1)]


def generate(instruction: dict) -> str:
    """Generate Manim code for the Bull vs Bear Projection effect."""
    data = instruction.get("data", {})
    optimistic_rate = data.get("optimistic_rate", 0.25)
    realistic_rate = data.get("realistic_rate", 0.10)
    pessimistic_rate = data.get("pessimistic_rate", -0.15)
    projection_years = data.get("projection_years", 3)
    projection_labels = data.get("projection_labels", ["Bull", "Base", "Bear"])
    title = instruction.get("title", "")

    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Historical line + three projected future paths."""

    def construct(self):
        self.camera.background_color = "#0F172A"

        optimistic_rate = {json.dumps(optimistic_rate)}
        realistic_rate = {json.dumps(realistic_rate)}
        pessimistic_rate = {json.dumps(pessimistic_rate)}
        projection_years = {json.dumps(projection_years)}
        projection_labels = {json.dumps(projection_labels)}
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
            err = Text("Insufficient data for projection", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        last_price = values[-1]
        n_hist = len(values)
        n_proj = projection_years

        # Compute projections
        rates = [optimistic_rate, realistic_rate, pessimistic_rate]
        projections = []
        for rate in rates:
            proj = [last_price * (1 + rate) ** y for y in range(n_proj + 1)]
            projections.append(proj)

        # Y range covers historical + all projections
        all_vals = list(values)
        for proj in projections:
            all_vals.extend(proj)
        y_min = min(all_vals) * 0.9
        y_max = max(all_vals) * 1.1

        total_x = n_hist + n_proj
        axes = Axes(
            x_range=[0, total_x - 1, max(1, total_x // 6)],
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

        # Draw historical line
        hist_points = [axes.c2p(i, v) for i, v in enumerate(values)]
        hist_line = VMobject(color="#2962FF", stroke_width=6)
        hist_line.set_points_smoothly(hist_points)
        self.play(Create(hist_line), run_time=1.2)

        # "Today" marker
        today_x = n_hist - 1
        today_line = DashedLine(
            axes.c2p(today_x, y_min), axes.c2p(today_x, y_max),
            color="#64748B", stroke_width=1, dash_length=0.1,
        )
        today_label = Text("Today", font_size=14, color="#64748B")
        today_label.next_to(axes.c2p(today_x, y_max), UP, buff=0.1)
        self.play(Create(today_line), FadeIn(today_label), run_time=0.3)
        self.wait(0.5)

        # Draw projection lines
        proj_colors = ["#10B981", "#64748B", "#EF4444"]
        for idx, (proj, color, label_text) in enumerate(zip(projections, proj_colors, projection_labels)):
            proj_points = [axes.c2p(today_x + i, v) for i, v in enumerate(proj)]
            proj_line = DashedLine(
                proj_points[0], proj_points[-1],
                color=color, stroke_width=2, dash_length=0.15,
            )
            # Actually draw as smooth dashed VMobject for multi-point
            proj_mob = VMobject(color=color, stroke_width=2)
            proj_mob.set_points_smoothly(proj_points)
            proj_mob.set_stroke(opacity=0.8)

            # End label with projected price
            end_price = proj[-1]
            end_label = Text(
                f"{{label_text}}: ${{end_price:,.0f}}",
                font=FONT, font_size=16, color=color,
            )
            end_label.next_to(axes.c2p(today_x + n_proj, end_price), RIGHT, buff=0.15)

            self.play(Create(proj_mob), run_time=0.5)
            self.play(FadeIn(end_label), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
