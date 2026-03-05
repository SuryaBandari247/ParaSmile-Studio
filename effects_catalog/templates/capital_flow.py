"""Capital Flow Effect — animated directional arrows between entities.

Renders animated arrows between labeled entities (assets, sectors, geographies)
with arrow thickness proportional to flow amount.
"""

from __future__ import annotations

import json
import logging
import math

logger = logging.getLogger(__name__)

SCENE_CLASS = "CapitalFlowScene"


def compute_arrow_width(flow_amount: float, max_amount: float, base_width: float = 2.0) -> float:
    """Compute arrow width proportional to flow amount."""
    if max_amount <= 0:
        return base_width
    return (flow_amount / max_amount) * base_width


def generate(instruction: dict) -> str:
    """Generate Manim code for the Capital Flow effect."""
    data = instruction.get("data", {})
    flows = data.get("flows", [])
    layout = data.get("layout", "horizontal")
    arrow_base_width = data.get("arrow_base_width", 2)
    flow_label_format = data.get("flow_label_format", "${:.1f}B")
    animation_duration = data.get("animation_duration", 4.0)
    title = instruction.get("title", "")

    return f'''from manim import *
import numpy as np

FONT = "Inter"
import math

class {SCENE_CLASS}(Scene):
    """Animated capital flow arrows between entities."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"

        flows = {json.dumps(flows)}
        layout = {json.dumps(layout)}
        arrow_base_width = {json.dumps(arrow_base_width)}
        flow_label_format = {json.dumps(flow_label_format)}
        animation_duration = {json.dumps(animation_duration)}
        title = {json.dumps(title)}

        if title:
            title_mob = Text(title, font=FONT, font_size=44, color="#111827", weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob), run_time=0.3)

        if not flows:
            err = Text("No flows to display", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(err))
            self.wait(3)
            return

        # Collect unique entities
        entities = []
        seen = set()
        for f in flows:
            for e in [f.get("from_entity", ""), f.get("to_entity", "")]:
                if e and e not in seen:
                    entities.append(e)
                    seen.add(e)

        n_entities = len(entities)
        max_amount = max((f.get("flow_amount", 0) for f in flows), default=1)

        # Position entities
        if layout == "circular":
            positions = {{}}
            for i, e in enumerate(entities):
                angle = math.pi / 2 + i * 2 * math.pi / n_entities
                positions[e] = np.array([3 * math.cos(angle), 3 * math.sin(angle), 0])
        else:
            # Horizontal layout
            positions = {{}}
            spacing = 10 / max(n_entities - 1, 1)
            for i, e in enumerate(entities):
                positions[e] = np.array([-5 + i * spacing, 0, 0])

        # Draw entity labels
        entity_mobs = {{}}
        for e in entities:
            box = RoundedRectangle(
                width=2, height=0.8, corner_radius=0.1,
                color="#2563EB", fill_color="#F9FAFB", fill_opacity=0.9,
                stroke_width=1.5,
            )
            label = Text(e, font=FONT, font_size=18, color="#111827")
            label.move_to(box)
            group = VGroup(box, label)
            group.move_to(positions[e])
            entity_mobs[e] = group

        self.play(
            LaggedStart(*[FadeIn(g) for g in entity_mobs.values()], lag_ratio=0.1),
            run_time=0.5,
        )

        # Draw flow arrows sequentially
        per_flow_dur = animation_duration / max(len(flows), 1)
        for f in flows:
            from_e = f.get("from_entity", "")
            to_e = f.get("to_entity", "")
            amount = f.get("flow_amount", 0)
            color = f.get("flow_color", "#FFD60A")

            if from_e not in positions or to_e not in positions:
                continue

            width = (amount / max_amount) * arrow_base_width if max_amount > 0 else arrow_base_width
            arrow = Arrow(
                positions[from_e], positions[to_e],
                color=color, stroke_width=max(width, 0.5),
                buff=1.2,
            )
            self.play(Create(arrow), run_time=per_flow_dur * 0.6)

            # Flow label
            label_text = flow_label_format.format(amount)
            label = Text(label_text, font=FONT, font_size=14, color=color)
            label.move_to(arrow.get_center() + UP * 0.3)
            self.play(FadeIn(label), run_time=per_flow_dur * 0.4)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
