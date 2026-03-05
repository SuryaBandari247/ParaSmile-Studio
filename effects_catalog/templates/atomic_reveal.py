"""Atomic Component Reveal Effect — exploded-view component breakdown.

Displays a central entity and animates component parts flying out radially
or in a grid layout, with sentiment color-coding and highlight emphasis
on the key driver or risk factor.
"""

from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger(__name__)

SCENE_CLASS = "AtomicRevealScene"


class ComponentNotFoundError(Exception):
    def __init__(self, name: str, available: list[str]):
        self.name = name
        self.available = available
        super().__init__(
            f"highlight_component '{name}' not found. "
            f"Available: {', '.join(available)}"
        )


SENTIMENT_COLORS = {
    "positive": "#10B981",
    "negative": "#EF4444",
    "neutral": "#6B7280",
}


def compute_radial_positions(n: int, radius: float = 3.0) -> list[tuple[float, float]]:
    """Compute evenly-spaced radial positions for n components."""
    return [
        (radius * math.cos(2 * math.pi * i / n),
         radius * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def compute_grid_positions(n: int, spacing: float = 2.5) -> list[tuple[float, float]]:
    """Compute grid positions for n components."""
    cols = math.ceil(math.sqrt(n))
    positions = []
    for i in range(n):
        row = i // cols
        col = i % cols
        x = (col - (cols - 1) / 2) * spacing
        y = -(row - (math.ceil(n / cols) - 1) / 2) * spacing
        positions.append((x, y))
    return positions


def generate(instruction: dict) -> str:
    """Generate Manim code for the Atomic Reveal effect."""
    data = instruction.get("data", {})
    entity_name = data.get("entity_name", "Entity")
    components = data.get("components", [])
    highlight_component = data.get("highlight_component", "")
    layout = data.get("layout", "radial")
    title = instruction.get("title", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"
import math

class {SCENE_CLASS}(Scene):
    """Central entity with exploded component reveal."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        entity_name = {json.dumps(entity_name)}
        components = {json.dumps(components)}
        highlight_component = {json.dumps(highlight_component)}
        layout = {json.dumps(layout)}
        title = {json.dumps(title)}

        sentiment_colors = {{
            "positive": "#10B981",
            "negative": "#EF4444",
            "neutral": "#6B7280",
        }}

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#111827", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        # Central entity block
        entity_box = RoundedRectangle(
            width=3, height=1.2, corner_radius=0.15,
            color="#2563EB", fill_color="#F9FAFB", fill_opacity=0.9,
            stroke_width=2,
        )
        entity_label = Text(entity_name, font=FONT, font_size=44, color="#111827", weight=BOLD)
        entity_label.move_to(entity_box)
        entity_group = VGroup(entity_box, entity_label)
        entity_group.move_to(ORIGIN)

        self.play(FadeIn(entity_group, scale=0.8), run_time=0.5)
        self.wait(0.3)

        n = len(components)
        if n == 0:
            self.wait(3)
            return

        # Compute positions
        radius = 3.0
        if layout == "grid":
            cols = math.ceil(math.sqrt(n))
            spacing = 2.5
            positions = []
            for i in range(n):
                row = i // cols
                col = i % cols
                x = (col - (cols - 1) / 2) * spacing
                y = -(row - (math.ceil(n / cols) - 1) / 2) * spacing - 0.5
                positions.append((x, y))
            # Shift entity up
            entity_group.animate.shift(UP * 2.5)
        else:
            positions = []
            for i in range(n):
                angle = math.pi / 2 + i * 2 * math.pi / n
                positions.append((radius * math.cos(angle), radius * math.sin(angle)))

        # Build component blocks
        comp_groups = []
        highlight_idx = None
        for i, comp in enumerate(components):
            name = comp.get("name", f"Component {{i}}")
            value = comp.get("value", "")
            sentiment = comp.get("sentiment", "neutral")
            color = sentiment_colors.get(sentiment, "#6B7280")

            box = RoundedRectangle(
                width=2.2, height=0.9, corner_radius=0.1,
                color=color, fill_color="#F9FAFB", fill_opacity=0.85,
                stroke_width=1.5,
            )
            name_text = Text(name, font=FONT, font_size=18, color="#111827")
            name_text.move_to(box.get_center() + UP * 0.12)
            val_text = Text(str(value), font_size=11, color=color)
            val_text.move_to(box.get_center() + DOWN * 0.18)

            group = VGroup(box, name_text, val_text)
            px, py = positions[i]
            group.move_to([px, py, 0])
            comp_groups.append(group)

            if name == highlight_component:
                highlight_idx = i

        # Animate components flying out with LaggedStart
        self.play(
            LaggedStart(
                *[FadeIn(g, shift=g.get_center() - entity_group.get_center())
                  for g in comp_groups],
                lag_ratio=0.12,
            ),
            run_time=max(1.0, n * 0.2),
        )

        # Highlight the key component
        if highlight_idx is not None:
            self.wait(0.3)
            self.play(
                Indicate(comp_groups[highlight_idx], color="#FFD60A", scale_factor=1.1),
                run_time=0.6,
            )

        # Fade in value labels (already visible, but pulse them)
        self.wait(0.5)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
