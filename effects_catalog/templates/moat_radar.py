"""Moat Comparison Radar Effect — spider/radar chart comparing two companies.

Renders a polar radar chart with N axes, two overlapping semi-transparent
polygons, sequential animation, and Indicate on the max-advantage axis.
"""

from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger(__name__)

SCENE_CLASS = "MoatRadarScene"


class LengthMismatchError(Exception):
    def __init__(self, len_a: int, len_b: int, len_labels: int):
        self.len_a = len_a
        self.len_b = len_b
        self.len_labels = len_labels
        super().__init__(
            f"Mismatched list lengths: company_a_values={len_a}, "
            f"company_b_values={len_b}, metric_labels={len_labels}"
        )


class RangeError(Exception):
    def __init__(self, value: float, index: int, company: str):
        self.value = value
        self.index = index
        self.company = company
        super().__init__(
            f"Value {value} at index {index} for {company} is outside 0-100 range"
        )


def find_max_advantage_index(values_a: list[float], values_b: list[float]) -> int:
    """Return the index where company A has the largest advantage over B."""
    if not values_a:
        return 0
    diffs = [a - b for a, b in zip(values_a, values_b)]
    return diffs.index(max(diffs))


def generate(instruction: dict) -> str:
    """Generate Manim code for the Moat Radar effect."""
    data = instruction.get("data", {})
    company_a_name = data.get("company_a_name", "Company A")
    company_a_values = data.get("company_a_values", [])
    company_b_name = data.get("company_b_name", "Company B")
    company_b_values = data.get("company_b_values", [])
    metric_labels = data.get("metric_labels", [])
    company_a_color = data.get("company_a_color", "#0A84FF")
    company_b_color = data.get("company_b_color", "#FF453A")
    title = instruction.get("title", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(Scene):
    """Spider/radar chart comparing two companies."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        company_a_name = {json.dumps(company_a_name)}
        company_b_name = {json.dumps(company_b_name)}
        company_a_values = {json.dumps(company_a_values)}
        company_b_values = {json.dumps(company_b_values)}
        metric_labels = {json.dumps(metric_labels)}
        company_a_color = {json.dumps(company_a_color)}
        company_b_color = {json.dumps(company_b_color)}
        title = {json.dumps(title)}

        n = len(metric_labels)
        if n < 3:
            err = Text("Need at least 3 metrics for radar", font=FONT, font_size=28, color="#EF5350")
            self.play(FadeIn(err))
            self.wait(3)
            return

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#191919", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        radius = 2.5
        center = DOWN * 0.3

        # Draw axes and labels
        axes_group = VGroup()
        label_group = VGroup()
        for i in range(n):
            angle = PI / 2 + i * TAU / n
            end_point = center + radius * np.array([np.cos(angle), np.sin(angle), 0])
            axis = Line(center, end_point, color="#9598A1", stroke_width=1)
            axes_group.add(axis)

            label = Text(metric_labels[i], font=FONT, font_size=16, color="#787B86")
            label_dir = np.array([np.cos(angle), np.sin(angle), 0])
            label.move_to(center + (radius + 0.4) * label_dir)
            label_group.add(label)

        # Concentric rings
        rings = VGroup()
        for r_frac in [0.25, 0.5, 0.75, 1.0]:
            ring_pts = []
            for i in range(n + 1):
                angle = PI / 2 + i * TAU / n
                ring_pts.append(center + radius * r_frac * np.array([np.cos(angle), np.sin(angle), 0]))
            ring = VMobject(color="#D6DCDE", stroke_width=0.5)
            ring.set_points_as_corners(ring_pts)
            rings.add(ring)

        self.play(Create(rings), Create(axes_group), run_time=0.5)
        self.play(FadeIn(label_group), run_time=0.3)

        # Company A polygon
        def make_polygon(vals, color):
            pts = []
            for i in range(n):
                angle = PI / 2 + i * TAU / n
                r = radius * (vals[i] / 100.0) if i < len(vals) else 0
                pts.append(center + r * np.array([np.cos(angle), np.sin(angle), 0]))
            pts.append(pts[0])  # close
            poly = VMobject(color=color, fill_color=color, fill_opacity=0.2, stroke_width=2)
            poly.set_points_as_corners(pts)
            return poly

        poly_a = make_polygon(company_a_values, company_a_color)
        poly_b = make_polygon(company_b_values, company_b_color)

        self.play(Create(poly_a), run_time=0.6)
        self.play(Create(poly_b), run_time=0.6)

        # Legend
        legend_a = VGroup(
            Dot(radius=0.06, color=company_a_color),
            Text(company_a_name, font=FONT, font_size=16, color=company_a_color),
        ).arrange(RIGHT, buff=0.1)
        legend_b = VGroup(
            Dot(radius=0.06, color=company_b_color),
            Text(company_b_name, font=FONT, font_size=16, color=company_b_color),
        ).arrange(RIGHT, buff=0.1)
        legend = VGroup(legend_a, legend_b).arrange(RIGHT, buff=0.5)
        legend.to_edge(DOWN, buff=0.2)
        self.play(FadeIn(legend), run_time=0.3)

        # Indicate max advantage axis
        if company_a_values and company_b_values:
            diffs = [a - b for a, b in zip(company_a_values, company_b_values)]
            max_idx = diffs.index(max(diffs))
            self.wait(0.5)
            self.play(
                Indicate(axes_group[max_idx], color="#FFD60A", scale_factor=1.3),
                Indicate(label_group[max_idx], color="#FFD60A", scale_factor=1.2),
                run_time=0.6,
            )

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
