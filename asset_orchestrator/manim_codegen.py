"""Manim code generator — produces runnable Manim scene files from Visual_Instructions.

Generates Python source code with real Manim Scene subclasses that have
the instruction data baked in, so `manim render` can produce actual MP4s.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

BACKGROUND_COLOR = "#FFFFFF"
TEXT_COLOR = "#111827"

# ── Documentary palette (Calm Capitalist house style) ──
# Deep blue primary, gray hierarchy, emerald/red accents.
# Defined in effects_catalog/palette.py — duplicated here for codegen.
ACCENT_COLORS = [
    "#2563EB",  # deep blue (primary)
    "#10B981",  # emerald
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#06B6D4",  # cyan
    "#F97316",  # orange
    "#EC4899",  # pink
]


def generate_scene_code(
    instruction: dict,
    registry: "EffectRegistry | None" = None,
    audio_timestamps: list[float] | None = None,
    quality_profile: str = "production",
) -> str:
    """Generate a complete Manim Python file for the given instruction.

    When *registry* is provided, uses catalog-driven dispatch:
      resolve → validate params → merge styles → render via legacy generator.
    Falls back to the hardcoded generators dict when registry is None.

    Args:
        instruction: Scene instruction dict with type, data, style_overrides.
        registry: EffectRegistry for skeleton lookup. None = legacy mode.
        audio_timestamps: Timestamps (seconds) from SynthesizerService,
            one per sync_point in the skeleton. Injects self.wait() calls.
        quality_profile: Render quality profile name ("draft" or "production").
    """
    vis_type = instruction.get("type", "text_overlay")

    # ── Registry-driven path ────────────────────────────────
    if registry is not None:
        from effects_catalog.exceptions import SyncPointMismatchError, UnknownProfileError
        from effects_catalog.schema_validator import SchemaValidator

        skeleton = registry.resolve(vis_type, instruction)

        # Validate params against skeleton schema
        raw_params = instruction.get("data", {})
        if skeleton.parameter_schema:
            validated = SchemaValidator.validate(raw_params, skeleton.parameter_schema)
            instruction = {**instruction, "data": validated}

        # Validate quality profile
        if quality_profile not in skeleton.quality_profiles:
            raise UnknownProfileError(quality_profile, list(skeleton.quality_profiles.keys()))

        # Sync point alignment
        if skeleton.sync_points and audio_timestamps is not None:
            if len(audio_timestamps) != len(skeleton.sync_points):
                raise SyncPointMismatchError(len(skeleton.sync_points), len(audio_timestamps))
            # Store sync waits on instruction for template use
            instruction = {
                **instruction,
                "_sync_waits": dict(zip(skeleton.sync_points, audio_timestamps)),
            }

        # Apply initial_wait from skeleton (overridable via style_overrides)
        style_overrides = instruction.get("style_overrides", {})
        effective_wait = style_overrides.get("initial_wait", skeleton.initial_wait)
        if effective_wait:
            instruction = {**instruction, "_initial_wait": effective_wait}

        logger.info(
            "Registry dispatch: %s → %s (quality=%s)",
            vis_type, skeleton.identifier, quality_profile,
        )
        # Fall through to legacy generators using the resolved identifier
        vis_type = skeleton.identifier

    # ── Legacy hardcoded dispatch ───────────────────────────
    generators = {
        "text_overlay": _gen_text_overlay,
        "bar_chart": _gen_bar_chart,
        "line_chart": _gen_line_chart,
        "pie_chart": _gen_pie_chart,
        "code_snippet": _gen_code_snippet,
        "reddit_post": _gen_reddit_post,
        "stat_callout": _gen_stat_callout,
        "quote_block": _gen_quote_block,
        "section_title": _gen_section_title,
        "bullet_reveal": _gen_bullet_reveal,
        "comparison": _gen_comparison,
        "fullscreen_statement": _gen_fullscreen_statement,
        "data_chart": _gen_data_chart,
        "timeseries": _gen_timeseries,
        "horizontal_bar": _gen_horizontal_bar,
        "grouped_bar": _gen_grouped_bar,
        "donut": _gen_donut_chart,
        "pdf_forensic": _gen_pdf_forensic,
        "forensic_zoom": _gen_forensic_zoom,
        "volatility_shadow": _gen_volatility_shadow,
        "relative_velocity": _gen_relative_velocity,
        "contextual_heatmap": _gen_contextual_heatmap,
        "bull_bear_projection": _gen_bull_bear_projection,
        "moat_radar": _gen_moat_radar,
        "atomic_reveal": _gen_atomic_reveal,
        "liquidity_shock": _gen_liquidity_shock,
        "momentum_glow": _gen_momentum_glow,
        "regime_shift": _gen_regime_shift,
        "speed_ramp": _gen_speed_ramp,
        "capital_flow": _gen_capital_flow,
        "compounding_explosion": _gen_compounding_explosion,
        "market_share_territory": _gen_market_share_territory,
        "historical_rank": _gen_historical_rank,
    }
    gen = generators.get(vis_type, _gen_text_overlay)
    code = gen(instruction)

    # ── Post-process: inject initial_wait and sync_waits into generated code ──
    if registry is not None:
        code = _inject_pacing(code, instruction)

    return code


def _inject_pacing(code: str, instruction: dict) -> str:
    """Post-process generated Manim code to inject pacing directives.

    Inserts initial_wait after the first self.play() call and appends
    sync_wait comments for narration alignment.
    """
    initial_wait = instruction.get("_initial_wait", 0.0)
    sync_waits = instruction.get("_sync_waits")

    if not initial_wait and not sync_waits:
        return code

    lines = code.split("\n")
    result = []
    first_play_injected = False

    for line in lines:
        result.append(line)
        # Inject initial_wait after the first self.play() call completes
        if not first_play_injected and initial_wait and "self.play(" in line and line.rstrip().endswith(")"):
            indent = len(line) - len(line.lstrip())
            pad = " " * indent
            result.append(f"{pad}self.wait({initial_wait})  # initial_wait: viewer orients")
            first_play_injected = True

    # Append sync_wait metadata as a comment block at the end for template use
    if sync_waits:
        result.append("")
        result.append("# ── Sync Points (narration alignment) ──")
        for point_name, timestamp in sync_waits.items():
            result.append(f"# sync_point: {point_name} @ {timestamp:.2f}s")

    return "\n".join(result)


def get_scene_class_name(instruction: dict) -> str:
    """Return the Manim Scene class name for the given instruction type."""
    names = {
        "text_overlay": "TextOverlayScene",
        "bar_chart": "BarChartScene",
        "line_chart": "LineChartScene",
        "pie_chart": "PieChartScene",
        "code_snippet": "CodeSnippetScene",
        "reddit_post": "RedditPostScene",
        "stat_callout": "StatCalloutScene",
        "quote_block": "QuoteBlockScene",
        "section_title": "SectionTitleScene",
        "bullet_reveal": "BulletRevealScene",
        "comparison": "ComparisonScene",
        "fullscreen_statement": "FullscreenStatementScene",
        "data_chart": "DataChartScene",
        "timeseries": "TimeseriesScene",
        "horizontal_bar": "HorizontalBarScene",
        "grouped_bar": "GroupedBarScene",
        "donut": "DonutChartScene",
    }
    return names.get(instruction.get("type", "text_overlay"), "TextOverlayScene")


def _gen_text_overlay(instruction: dict) -> str:
    title = instruction.get("title", "")
    text = instruction.get("data", {}).get("text", "")
    return f'''from manim import *

class TextOverlayScene(Scene):
    def construct(self):
        self.camera.background_color = "{BACKGROUND_COLOR}"
        title = Text({json.dumps(title)}, font_size=36, color="{TEXT_COLOR}")
        title.to_edge(UP, buff=0.5)
        body = Text({json.dumps(text)}, font_size=28, color="{TEXT_COLOR}", line_spacing=1.2)
        body.next_to(title, DOWN, buff=0.5)
        if body.width > 12:
            body.scale_to_fit_width(12)
        self.play(FadeIn(title, shift=UP * 0.3), run_time=0.5)
        self.play(FadeIn(body, shift=UP * 0.2), run_time=0.5)
        self.wait(3)
        self.play(FadeOut(title), FadeOut(body), run_time=0.5)
'''



def _gen_bar_chart(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    source = data.get("source", "")
    highlights = data.get("highlights", [])
    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(labels))]
    return f'''from manim import *

class BarChartScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"
        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        labels = {json.dumps(labels)}
        values = {json.dumps(values)}
        colors = {json.dumps(colors)}
        source = {json.dumps(source)}
        highlights = {json.dumps(highlights)}

        if not values:
            self.wait(3)
            return

        max_val = max(values) if values else 10
        n = len(values)
        bar_width = min(0.8, 9.0 / max(n, 1))
        bar_gap = bar_width * 0.3

        # Build axes area
        axes = Axes(
            x_range=[0, n, 1],
            y_range=[0, max_val * 1.25, max_val * 0.25 or 1],
            x_length=10.5,
            y_length=5,
            axis_config={{"color": "#c0c0c0", "include_ticks": False, "stroke_width": 1.5}},
        )
        axes.next_to(title, DOWN, buff=0.4)

        # Subtle grid
        grid = VGroup()
        y_step = max_val * 0.25 if max_val > 0 else 2
        for i in range(1, 5):
            y_val = i * y_step
            if y_val <= max_val * 1.25:
                line = DashedLine(
                    axes.c2p(0, y_val), axes.c2p(n, y_val),
                    color="#e0e0e0", stroke_width=0.8, dash_length=0.15,
                )
                grid.add(line)

        self.play(Create(axes), FadeIn(grid), run_time=0.5)

        # Progressive bar reveal with value labels
        bars = VGroup()
        value_labels = VGroup()
        x_labels = VGroup()

        for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
            # X label
            x_lbl = Text(str(lbl), font_size=14, color="{MUTED}")
            x_lbl.next_to(axes.c2p(i + 0.5, 0), DOWN, buff=0.15)
            x_labels.add(x_lbl)

            # Bar — built manually for control
            bottom = axes.c2p(i + 0.5 - bar_width / 2, 0)
            top = axes.c2p(i + 0.5 - bar_width / 2, val)
            bar_h = abs(top[1] - bottom[1])

            bar = RoundedRectangle(
                corner_radius=0.05,
                width=bar_width, height=bar_h,
                color=col, fill_opacity=0.9, stroke_width=0,
            )
            bar.move_to(axes.c2p(i + 0.5, val / 2))
            bars.add(bar)

            # Value label
            val_lbl = Text(f"{{val:,.1f}}" if val < 1000 else f"{{val:,.0f}}", font_size=14, color=col, weight=BOLD)
            val_lbl.next_to(bar, UP, buff=0.1)
            value_labels.add(val_lbl)

        self.play(FadeIn(x_labels), run_time=0.3)

        # Staggered bar growth
        self.play(
            LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.15),
            run_time=max(1.0, n * 0.2),
        )
        self.play(FadeIn(value_labels), run_time=0.3)

        # Indicate the highest bar
        if values:
            max_idx = values.index(max(values))
            self.play(Indicate(bars[max_idx], scale_factor=1.08, color="#FF1744"), run_time=0.5)

        # Indicate specific highlights
        for hl in highlights:
            idx = hl.get("index")
            if idx is not None and idx < len(bars):
                self.play(Indicate(bars[idx], scale_factor=1.08, color="#FF1744"), run_time=0.4)

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''



def _gen_line_chart(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    source = data.get("source", "")
    highlights = data.get("highlights", [])
    return f'''from manim import *
import numpy as np

class LineChartScene(MovingCameraScene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"
        self.camera.frame.save_state()

        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        values = {json.dumps(values)}
        labels = {json.dumps(labels)}
        source = {json.dumps(source)}
        highlights = {json.dumps(highlights)}

        if not values:
            self.wait(3)
            return

        axes = Axes(
            x_range=[0, len(values), 1],
            y_range=[0, max(values) * 1.2 if values else 10, max(values) * 0.2 if values else 2],
            x_length=10,
            y_length=5,
            axis_config={{"color": "#c0c0c0"}},
        )
        axes.next_to(title, DOWN, buff=0.4)

        # X-axis labels
        x_labels = VGroup()
        step = max(1, len(labels) // 6)
        for i in range(0, len(labels), step):
            lbl = Text(str(labels[i])[:10], font_size=12, color="{MUTED}")
            lbl.next_to(axes.c2p(i, 0), DOWN, buff=0.15)
            x_labels.add(lbl)

        self.play(Create(axes), FadeIn(x_labels), run_time=0.6)

        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="{ACCENT_COLORS[0]}", stroke_width=3)
        line.set_points_smoothly(points)

        # Camera zoom into chart, then track the line draw
        self.play(
            self.camera.frame.animate.set(width=13).move_to(axes.get_center()),
            run_time=0.3,
        )
        self.play(Create(line), run_time=1.5)

        # Dots at data points
        dots = VGroup(*[Dot(p, radius=0.05, color="{ACCENT_COLORS[1]}") for p in points])
        self.play(FadeIn(dots), run_time=0.4)

        # Restore camera
        self.play(Restore(self.camera.frame), run_time=0.4)

        # Indicate highlights
        for hl in highlights:
            idx = hl.get("index")
            hl_label = hl.get("label", "")
            if idx is not None and idx < len(dots):
                self.play(Indicate(dots[idx], scale_factor=2.5, color="#ff6b6b"), run_time=0.4)
                if hl_label:
                    hl_text = Text(hl_label, font_size=13, color="#ef4444", weight=BOLD)
                    hl_text.next_to(points[idx], UP, buff=0.2)
                    self.play(FadeIn(hl_text), run_time=0.2)

        # Indicate max point automatically
        if values and not highlights:
            max_idx = values.index(max(values))
            self.play(Indicate(dots[max_idx], scale_factor=2, color="#ff6b6b"), run_time=0.3)

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''


def _gen_pie_chart(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(labels))]
    return f'''from manim import *
import numpy as np

class PieChartScene(Scene):
    def construct(self):
        self.camera.background_color = "{BACKGROUND_COLOR}"
        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}")
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        values = {json.dumps(values)}
        labels = {json.dumps(labels)}
        colors = {json.dumps(colors)}
        total = sum(values)

        sectors = VGroup()
        label_group = VGroup()
        start_angle = 0
        for i, (val, lbl, col) in enumerate(zip(values, labels, colors)):
            angle = (val / total) * TAU
            sector = AnnularSector(
                inner_radius=0, outer_radius=2,
                angle=angle, start_angle=start_angle,
                color=col, fill_opacity=0.85,
            )
            sectors.add(sector)
            mid_angle = start_angle + angle / 2
            label_pos = 2.5 * np.array([np.cos(mid_angle), np.sin(mid_angle), 0])
            pct = f"{{val/total*100:.0f}}%"
            label = Text(f"{{lbl}}\\n{{pct}}", font_size=18, color="{TEXT_COLOR}")
            label.move_to(label_pos)
            label_group.add(label)
            start_angle += angle

        chart = VGroup(sectors, label_group)
        chart.next_to(title, DOWN, buff=0.4)
        self.play(Create(sectors), run_time=1.5)
        self.play(FadeIn(label_group), run_time=0.5)
        self.wait(3)
        self.play(FadeOut(chart), FadeOut(title), run_time=0.5)
'''


def _gen_code_snippet(instruction: dict) -> str:
    data = instruction.get("data", {})
    code = data.get("code", "# empty")
    language = data.get("language", "python")
    title = instruction.get("title", "")
    return f'''from manim import *

class CodeSnippetScene(Scene):
    def construct(self):
        self.camera.background_color = "{BACKGROUND_COLOR}"
        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}")
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        code = Code(
            code_string={json.dumps(code)},
            language={json.dumps(language)},
            tab_width=4,
            background="rectangle",
            formatter_style="monokai",
        )
        code.next_to(title, DOWN, buff=0.4)
        if code.width > 12:
            code.scale_to_fit_width(12)
        self.play(FadeIn(code, shift=UP * 0.3), run_time=0.8)
        self.wait(4)
        self.play(FadeOut(code), FadeOut(title), run_time=0.5)
'''


# ── YouTube-style scene generators ────────────────────────────────────────

BG_DARK = "#FFFFFF"
ACCENT_RED = "#FF453A"
ACCENT_BLUE = "#5AC8FA"
REDDIT_ORANGE = "#FF4500"
REDDIT_BG = "#F5F5F5"
REDDIT_CARD = "#FFFFFF"
MUTED = "#888888"


def _gen_reddit_post(instruction: dict) -> str:
    data = instruction.get("data", {})
    subreddit = data.get("subreddit", "r/unknown")
    post_title = data.get("post_title", "")
    upvotes = data.get("upvotes", 0)
    comments = data.get("comments", 0)
    username = data.get("username", "u/anonymous")
    return f'''from manim import *

class RedditPostScene(Scene):
    def construct(self):
        self.camera.background_color = "{REDDIT_BG}"

        # Card background
        card = RoundedRectangle(
            corner_radius=0.15, width=11, height=5.5,
            color="{REDDIT_CARD}", fill_opacity=1, stroke_width=0,
        )
        card.shift(DOWN * 0.2)
        self.add(card)

        # Subreddit header
        sub_dot = Dot(radius=0.12, color="{REDDIT_ORANGE}").shift(LEFT * 4.8 + UP * 2.1)
        sub_text = Text({json.dumps(subreddit)}, font_size=22, color="{REDDIT_ORANGE}", weight=BOLD)
        sub_text.next_to(sub_dot, RIGHT, buff=0.15)
        user_text = Text("Posted by {username}", font_size=16, color="{MUTED}")
        user_text.next_to(sub_text, RIGHT, buff=0.3)

        self.play(FadeIn(sub_dot), FadeIn(sub_text), FadeIn(user_text), run_time=0.4)

        # Post title
        title = Text({json.dumps(post_title)}, font_size=28, color="#2d2d3f", line_spacing=1.3)
        title.move_to(ORIGIN)
        if title.width > 10:
            title.scale_to_fit_width(10)
        self.play(FadeIn(title, shift=UP * 0.2), run_time=0.5)

        # Vote bar on left
        up_arrow = Triangle(color="{REDDIT_ORANGE}", fill_opacity=1).scale(0.15)
        up_arrow.move_to(LEFT * 5.2 + DOWN * 0.5)
        vote_count = Text({json.dumps(str(upvotes))}, font_size=20, color="#2d2d3f", weight=BOLD)
        vote_count.next_to(up_arrow, DOWN, buff=0.15)
        down_arrow = Triangle(color="{MUTED}", fill_opacity=0.5).scale(0.15).rotate(PI)
        down_arrow.next_to(vote_count, DOWN, buff=0.15)

        self.play(FadeIn(up_arrow), FadeIn(vote_count), FadeIn(down_arrow), run_time=0.3)

        # Comment count at bottom
        comment_icon = Text("💬", font_size=18)
        comment_icon.move_to(LEFT * 3.5 + DOWN * 2.2)
        comment_text = Text(f"{comments} Comments", font_size=16, color="{MUTED}")
        comment_text.next_to(comment_icon, RIGHT, buff=0.15)
        self.play(FadeIn(comment_icon), FadeIn(comment_text), run_time=0.3)

        self.wait(3.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_stat_callout(instruction: dict) -> str:
    data = instruction.get("data", {})
    value = data.get("value", "0")
    label = data.get("label", "")
    subtitle = data.get("subtitle", "")
    return f'''from manim import *

class StatCalloutScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        # Big number
        stat = Text({json.dumps(str(value))}, font_size=96, color="{ACCENT_RED}", weight=BOLD)
        stat.move_to(UP * 0.5)

        # Label
        label = Text({json.dumps(label)}, font_size=36, color="#1a1a2e", weight=BOLD)
        label.next_to(stat, DOWN, buff=0.4)

        # Subtitle
        subtitle = Text({json.dumps(subtitle)}, font_size=22, color="{MUTED}")
        subtitle.next_to(label, DOWN, buff=0.3)

        # Dramatic entrance
        self.play(GrowFromCenter(stat), run_time=0.6)
        self.play(FadeIn(label, shift=UP * 0.2), run_time=0.4)
        if {repr(subtitle.strip() != "")}:
            self.play(FadeIn(subtitle, shift=UP * 0.1), run_time=0.3)

        # Pulse effect on the number
        self.play(stat.animate.scale(1.1), run_time=0.2)
        self.play(stat.animate.scale(1/1.1), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_quote_block(instruction: dict) -> str:
    data = instruction.get("data", {})
    quote = data.get("quote", "")
    attribution = data.get("attribution", "")
    return f'''from manim import *

class QuoteBlockScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        # Quote mark
        open_quote = Text("\\u201C", font_size=120, color="{ACCENT_RED}")
        open_quote.move_to(LEFT * 5 + UP * 2)
        open_quote.set_opacity(0.4)
        self.add(open_quote)

        # Accent bar on left
        bar = Rectangle(width=0.08, height=3.5, color="{ACCENT_RED}", fill_opacity=1, stroke_width=0)
        bar.move_to(LEFT * 4.5)

        # Quote text
        quote = Text({json.dumps(quote)}, font_size=28, color="#1a1a2e", line_spacing=1.4)
        quote.move_to(RIGHT * 0.3 + UP * 0.3)
        if quote.width > 9:
            quote.scale_to_fit_width(9)

        # Attribution
        attr = Text({json.dumps("— " + attribution if attribution else "")}, font_size=20, color="{MUTED}", slant=ITALIC)
        attr.next_to(quote, DOWN, buff=0.5)
        attr.align_to(quote, LEFT)

        self.play(FadeIn(bar), run_time=0.3)
        self.play(FadeIn(quote, shift=RIGHT * 0.3), run_time=0.6)
        if {repr(bool(attribution))}:
            self.play(FadeIn(attr, shift=UP * 0.1), run_time=0.3)

        self.wait(3.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_section_title(instruction: dict) -> str:
    data = instruction.get("data", {})
    heading = data.get("heading", "")
    subtitle = data.get("subtitle", "")
    number = data.get("number", "")
    return f'''from manim import *

class SectionTitleScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        elements = []

        # Section number (if provided)
        number_str = {json.dumps(str(number))}
        if number_str:
            num = Text(number_str, font_size=72, color="{ACCENT_RED}", weight=BOLD)
            num.move_to(UP * 1.5)
            elements.append(num)
            self.play(FadeIn(num, scale=0.5), run_time=0.4)

        # Heading
        heading = Text({json.dumps(heading)}, font_size=52, color="#1a1a2e", weight=BOLD)
        if number_str:
            heading.next_to(elements[-1], DOWN, buff=0.4)
        else:
            heading.move_to(UP * 0.3)
        if heading.width > 12:
            heading.scale_to_fit_width(12)
        elements.append(heading)
        self.play(FadeIn(heading, shift=UP * 0.3), run_time=0.5)

        # Accent underline
        underline = Line(
            heading.get_left() + DOWN * 0.2,
            heading.get_right() + DOWN * 0.2,
            color="{ACCENT_RED}", stroke_width=4,
        )
        elements.append(underline)
        self.play(Create(underline), run_time=0.3)

        # Subtitle
        subtitle_str = {json.dumps(subtitle)}
        if subtitle_str:
            sub = Text(subtitle_str, font_size=26, color="{MUTED}")
            sub.next_to(underline, DOWN, buff=0.4)
            if sub.width > 11:
                sub.scale_to_fit_width(11)
            elements.append(sub)
            self.play(FadeIn(sub, shift=UP * 0.1), run_time=0.3)

        self.wait(2.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_bullet_reveal(instruction: dict) -> str:
    data = instruction.get("data", {})
    heading = data.get("heading", "")
    bullets = data.get("bullets", [])
    return f'''from manim import *

class BulletRevealScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        # Heading
        heading = Text({json.dumps(heading)}, font_size=36, color="#1a1a2e", weight=BOLD)
        heading.to_edge(UP, buff=0.6)
        if heading.width > 12:
            heading.scale_to_fit_width(12)
        self.play(FadeIn(heading, shift=DOWN * 0.2), run_time=0.4)

        # Underline
        underline = Line(
            heading.get_left() + DOWN * 0.15,
            heading.get_right() + DOWN * 0.15,
            color="{ACCENT_RED}", stroke_width=3,
        )
        self.play(Create(underline), run_time=0.2)

        bullets = {json.dumps(bullets)}
        bullet_mobs = []
        prev = underline

        for i, bullet_text in enumerate(bullets):
            dot = Dot(radius=0.06, color="{ACCENT_RED}")
            text = Text(bullet_text, font_size=24, color="#2d2d3f", line_spacing=1.2)
            if text.width > 10:
                text.scale_to_fit_width(10)
            text.next_to(prev, DOWN, buff=0.35, aligned_edge=LEFT)
            text.shift(RIGHT * 0.4)
            dot.next_to(text, LEFT, buff=0.2)
            bullet_mobs.extend([dot, text])
            self.play(FadeIn(dot), FadeIn(text, shift=LEFT * 0.2), run_time=0.4)
            prev = text

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_comparison(instruction: dict) -> str:
    data = instruction.get("data", {})
    left_title = data.get("left_title", "Option A")
    left_items = data.get("left_items", [])
    right_title = data.get("right_title", "Option B")
    right_items = data.get("right_items", [])
    title = instruction.get("title", "")
    return f'''from manim import *

class ComparisonScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        # Title
        title = Text({json.dumps(title)}, font_size=32, color="#1a1a2e", weight=BOLD)
        title.to_edge(UP, buff=0.4)
        self.play(FadeIn(title), run_time=0.3)

        # Divider line
        divider = Line(UP * 2, DOWN * 2.5, color="{MUTED}", stroke_width=2)
        self.play(Create(divider), run_time=0.3)

        # Left column
        left_head = Text({json.dumps(left_title)}, font_size=28, color="{ACCENT_RED}", weight=BOLD)
        left_head.move_to(LEFT * 3.5 + UP * 1.5)
        self.play(FadeIn(left_head), run_time=0.3)

        left_items = {json.dumps(left_items)}
        prev = left_head
        for item in left_items:
            t = Text("• " + item, font_size=20, color="#2d2d3f")
            t.next_to(prev, DOWN, buff=0.25, aligned_edge=LEFT)
            if t.width > 5.5:
                t.scale_to_fit_width(5.5)
            self.play(FadeIn(t, shift=LEFT * 0.1), run_time=0.25)
            prev = t

        # Right column
        right_head = Text({json.dumps(right_title)}, font_size=28, color="#4FC3F7", weight=BOLD)
        right_head.move_to(RIGHT * 3.5 + UP * 1.5)
        self.play(FadeIn(right_head), run_time=0.3)

        right_items = {json.dumps(right_items)}
        prev = right_head
        for item in right_items:
            t = Text("• " + item, font_size=20, color="#2d2d3f")
            t.next_to(prev, DOWN, buff=0.25, aligned_edge=LEFT)
            if t.width > 5.5:
                t.scale_to_fit_width(5.5)
            self.play(FadeIn(t, shift=LEFT * 0.1), run_time=0.25)
            prev = t

        self.wait(3.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.4)
'''


def _gen_fullscreen_statement(instruction: dict) -> str:
    data = instruction.get("data", {})
    statement = data.get("statement", "")
    emphasis_word = data.get("emphasis_word", "")
    return f'''from manim import *

class FullscreenStatementScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        statement = {json.dumps(statement)}
        emphasis = {json.dumps(emphasis_word)}

        if emphasis and emphasis in statement:
            parts = statement.split(emphasis, 1)
            before = Text(parts[0], font_size=42, color="#1a1a2e")
            emph = Text(emphasis, font_size=42, color="{ACCENT_RED}", weight=BOLD)
            after = Text(parts[1] if len(parts) > 1 else "", font_size=42, color="#1a1a2e")
            group = VGroup(before, emph, after).arrange(RIGHT, buff=0.1)
        else:
            group = Text(statement, font_size=42, color="#1a1a2e", line_spacing=1.3)

        if group.width > 12:
            group.scale_to_fit_width(12)

        self.play(FadeIn(group, shift=UP * 0.3), run_time=0.7)
        self.wait(3.5)
        self.play(FadeOut(group, shift=DOWN * 0.2), run_time=0.4)
'''


# ── Yahoo Finance enrichment ──────────────────────────────────────────────




def _enrich_from_yahoo(data: dict) -> dict:
    """Fetch live price history from Yahoo Finance if data has ticker fields.

    Only runs when data doesn't already have `values`/`series` populated.
    Returns enriched copy of data dict with events converted to index positions.
    If events reference dates outside the requested period, the period is
    automatically extended to cover them.
    """
    from datetime import datetime, timedelta

    tickers = data.get("tickers") or []
    single = data.get("ticker", "")
    if single and single not in tickers:
        tickers = [single] + tickers
    if not tickers:
        return data

    if data.get("values") or data.get("series"):
        return data

    period = data.get("period", "1y")
    interval = data.get("interval", "1wk")
    value_type = data.get("value_type", "close")

    # Check if any events require extending the period
    events = data.get("events", [])
    if events:
        earliest_event = None
        for evt in events:
            evt_date = evt.get("date", "")
            if evt_date:
                try:
                    ed = datetime.strptime(evt_date[:10], "%Y-%m-%d")
                    if earliest_event is None or ed < earliest_event:
                        earliest_event = ed
                except Exception:
                    pass

        if earliest_event:
            # Calculate how far back the requested period goes
            period_map = {
                "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365,
                "2y": 730, "5y": 1825, "10y": 3650, "max": 36500,
            }
            period_days = period_map.get(period, 365)
            cutoff = datetime.now() - timedelta(days=period_days)

            if earliest_event < cutoff:
                # Extend period to cover the event + 30 day buffer
                needed_days = (datetime.now() - earliest_event).days + 30
                # Pick the smallest standard period that covers it
                for p, d in sorted(period_map.items(), key=lambda x: x[1]):
                    if d >= needed_days:
                        period = p
                        break
                else:
                    period = "max"
                logger.info("Extended period from %s to %s to cover event at %s",
                            data.get("period", "1y"), period, earliest_event.strftime("%Y-%m-%d"))

    try:
        import yfinance as yf

        series_list = []
        all_dates = None

        for symbol in tickers[:5]:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                logger.warning("No Yahoo Finance data for %s", symbol)
                continue

            dates = [d.strftime("%Y-%m-%d") for d in hist.index]
            if all_dates is None:
                all_dates = dates

            if value_type == "pct_change":
                base = hist["Close"].iloc[0]
                values = [round(((v / base) - 1) * 100, 2) for v in hist["Close"]]
            else:
                values = [round(float(v), 2) for v in hist["Close"]]

            series_list.append({"name": symbol, "values": values})

        if series_list and all_dates:
            data = dict(data)
            data["dates"] = all_dates
            data["series"] = series_list
            if "chart_type" not in data:
                data["chart_type"] = "timeseries"
            if not data.get("source"):
                data["source"] = "Yahoo Finance"

            # Convert event dates to index positions
            if events and all_dates:
                resolved_events = []
                for evt in events:
                    evt_date = evt.get("date", "")
                    evt_label = evt.get("label", "")
                    if evt_date:
                        best_idx = 0
                        best_dist = float("inf")
                        try:
                            target = datetime.strptime(evt_date[:10], "%Y-%m-%d")
                            for i, d in enumerate(all_dates):
                                d1 = datetime.strptime(d[:10], "%Y-%m-%d")
                                dist = abs((d1 - target).days)
                                if dist < best_dist:
                                    best_dist = dist
                                    best_idx = i
                        except Exception:
                            best_idx = len(all_dates) // 2

                        resolved_events.append({"index": best_idx, "label": evt_label})
                        logger.info("Event '%s' at date %s → index %d (closest: %s, %d days off)",
                                    evt_label, evt_date, best_idx,
                                    all_dates[best_idx] if best_idx < len(all_dates) else "?",
                                    best_dist)
                    elif "index" in evt:
                        resolved_events.append(evt)
                data["events"] = resolved_events

            logger.info(
                "Enriched chart with Yahoo Finance: %d tickers, %d points, %d events",
                len(series_list), len(all_dates), len(data.get("events", [])),
            )
    except ImportError:
        logger.warning("yfinance not installed — skipping enrichment")
    except Exception as exc:
        logger.warning("Yahoo Finance enrichment failed: %s", exc)

    return data




# ── Data chart dispatcher (replaces data_chart_renderer.py) ───────────────


def _gen_data_chart(instruction: dict) -> str:
    """Route a data_chart instruction to the appropriate Manim generator.

    Handles yfinance enrichment, then dispatches by chart_type.
    """
    data = instruction.get("data", {})
    data = _enrich_from_yahoo(data)
    instruction = dict(instruction, data=data)

    chart_type = data.get("chart_type", "bar")
    router = {
        "bar": _gen_bar_chart,
        "line": _gen_line_chart,
        "area": _gen_line_chart,
        "pie": _gen_pie_chart,
        "donut": _gen_donut_chart,
        "timeseries": _gen_timeseries,
        "horizontal_bar": _gen_horizontal_bar,
        "grouped_bar": _gen_grouped_bar,
    }
    gen = router.get(chart_type, _gen_bar_chart)
    return gen(instruction)


# ── Timeseries (multi-line, animated draw) ────────────────────────────────



def _gen_timeseries(instruction: dict) -> str:
    data = instruction.get("data", {})
    title = instruction.get("title", "")
    dates = data.get("dates", []) or data.get("labels", [])
    series_list = data.get("series", [])
    if not series_list and "values" in data:
        series_list = [{"name": data.get("series_name", ""), "values": data["values"]}]
    source = data.get("source", "")
    is_pct = data.get("value_type") == "pct_change"
    events = data.get("events", [])
    highlights = data.get("highlights", [])

    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(series_list))]

    # Vibrant palette constants for generated code
    GREEN_UP = "#00E676"
    RED_DOWN = "#FF5252"

    return f'''from manim import *
import numpy as np

class TimeseriesScene(MovingCameraScene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"
        self.camera.frame.save_state()

        # Title
        title = Text({json.dumps(title)}, font_size=30, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        series_list = {json.dumps(series_list)}
        dates = {json.dumps(dates)}
        colors = {json.dumps(colors)}
        is_pct = {repr(is_pct)}
        source = {json.dumps(source)}
        events = {json.dumps(events)}
        highlights = {json.dumps(highlights)}

        GREEN_UP = "{GREEN_UP}"
        RED_DOWN = "{RED_DOWN}"

        n = len(dates)
        if n < 2 or not series_list:
            self.wait(3)
            return

        # Compute global y range
        all_vals = [v for s in series_list for v in s.get("values", [])]
        y_min = min(0, min(all_vals)) if all_vals else 0
        y_max = max(all_vals) * 1.15 if all_vals else 10
        if y_max == y_min:
            y_max = y_min + 10

        axes = Axes(
            x_range=[0, n - 1, max(1, n // 6)],
            y_range=[y_min, y_max, (y_max - y_min) / 5],
            x_length=10.5,
            y_length=5,
            axis_config={{"color": "#c0c0c0", "include_ticks": True, "stroke_width": 1.5}},
        )
        axes.next_to(title, DOWN, buff=0.35)

        # Subtle horizontal grid lines
        grid = VGroup()
        y_step = (y_max - y_min) / 5
        for i in range(1, 5):
            y_val = y_min + i * y_step
            line = DashedLine(
                axes.c2p(0, y_val), axes.c2p(n - 1, y_val),
                color="#e0e0e0", stroke_width=0.8, dash_length=0.15,
            )
            grid.add(line)

        # X-axis date labels
        step = max(1, n // 6)
        x_labels = VGroup()
        for i in range(0, n, step):
            if i < len(dates):
                lbl = Text(dates[i][:7], font_size=12, color="{MUTED}")
                lbl.next_to(axes.c2p(i, y_min), DOWN, buff=0.15)
                x_labels.add(lbl)

        self.play(Create(axes), FadeIn(x_labels), FadeIn(grid), run_time=0.6)

        # Zero line for pct_change
        if is_pct and y_min < 0:
            zero_line = DashedLine(
                axes.c2p(0, 0), axes.c2p(n - 1, 0),
                color="#8b949e", stroke_width=1.2,
            )
            self.play(Create(zero_line), run_time=0.2)

        # Gentle camera push into chart area
        self.play(
            self.camera.frame.animate.set(width=13).move_to(axes.get_center()),
            run_time=0.5,
        )

        # ── Draw each series ──
        all_badges = VGroup()
        legend_items = VGroup()

        for idx, series in enumerate(series_list):
            vals = [float(v) for v in series.get("values", [])][:n]
            base_color = colors[idx % len(colors)]
            name = series.get("name", "")

            points = [axes.c2p(i, v) for i, v in enumerate(vals)]

            # Build colored segments: green for up, red for down
            segments = VGroup()
            for i in range(len(vals) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                going_down = vals[i + 1] < vals[i]
                seg_color = RED_DOWN if going_down else (base_color if len(series_list) > 1 else GREEN_UP)
                seg = Line(p1, p2, color=seg_color, stroke_width=2.5)
                segments.add(seg)

            # Fast smooth draw — single animation, camera gently drifts right
            draw_time = min(2.0, max(0.8, n * 0.008))
            self.play(
                LaggedStart(*[Create(seg) for seg in segments], lag_ratio=0.005),
                self.camera.frame.animate.move_to(
                    axes.get_center() * 0.7 + np.array(points[-1]) * 0.3
                ),
                run_time=draw_time,
                rate_func=smooth,
            )

            # Glow effect — faint wider line behind for depth
            glow = VMobject(color=base_color, stroke_width=7, stroke_opacity=0.12)
            glow.set_points_smoothly(points)
            self.add(glow)
            self.mobjects.insert(0, self.mobjects.pop())

            # End-of-line value badge
            end_val = vals[-1]
            if is_pct:
                badge_text = f"+{{end_val:.1f}}%" if end_val >= 0 else f"{{end_val:.1f}}%"
                badge_color = GREEN_UP if end_val >= 0 else RED_DOWN
            else:
                badge_text = f"${{end_val:,.0f}}" if end_val > 100 else f"{{end_val:,.2f}}"
                badge_color = base_color

            badge_bg = RoundedRectangle(
                corner_radius=0.08, width=1.4, height=0.35,
                color=badge_color, fill_opacity=0.15, stroke_width=1, stroke_color=badge_color,
            )
            badge_label = Text(badge_text, font_size=16, color=badge_color, weight=BOLD)
            badge = VGroup(badge_bg, badge_label)
            badge_label.move_to(badge_bg.get_center())
            badge.next_to(points[-1], RIGHT, buff=0.15)
            self.play(FadeIn(badge, scale=0.8), run_time=0.2)
            all_badges.add(badge)

            # Legend entry
            if name:
                dot = Dot(radius=0.06, color=base_color)
                lbl = Text(name, font_size=14, color="{TEXT_COLOR}")
                entry = VGroup(dot, lbl).arrange(RIGHT, buff=0.1)
                legend_items.add(entry)

        # Restore camera to full view before events
        self.play(Restore(self.camera.frame), run_time=0.4)

        # ── Event markers — zoom into the event date ──
        for evt in events:
            evt_idx = evt.get("index")
            evt_label = evt.get("label", "")
            if evt_idx is not None and 0 <= evt_idx < n:
                # Vertical marker line
                marker = DashedLine(
                    axes.c2p(evt_idx, y_min),
                    axes.c2p(evt_idx, y_max * 0.95),
                    color=RED_DOWN, stroke_width=2, dash_length=0.1,
                )
                marker_label = Text(evt_label, font_size=13, color=RED_DOWN, weight=BOLD)
                marker_label.next_to(axes.c2p(evt_idx, y_max * 0.88), UP, buff=0.1)
                if marker_label.width > 2.5:
                    marker_label.scale_to_fit_width(2.5)

                # Camera zooms into the event region
                evt_point = axes.c2p(evt_idx, y_min + (y_max - y_min) * 0.5)
                self.play(
                    Create(marker),
                    FadeIn(marker_label),
                    self.camera.frame.animate.set(width=7).move_to(evt_point),
                    run_time=0.5,
                )

                # Pulse the event data point
                if series_list:
                    evt_vals = series_list[0].get("values", [])
                    if evt_idx < len(evt_vals):
                        evt_dot = Dot(
                            axes.c2p(evt_idx, float(evt_vals[evt_idx])),
                            radius=0.1, color=RED_DOWN,
                        )
                        self.play(FadeIn(evt_dot), run_time=0.1)
                        self.play(
                            Indicate(evt_dot, scale_factor=2, color="#FF453A"),
                            run_time=0.4,
                        )

                # Brief hold then pull back
                self.wait(0.5)
                self.play(Restore(self.camera.frame), run_time=0.4)

        # ── Indicate highlights ──
        for hl in highlights:
            hl_idx = hl.get("index")
            hl_series = hl.get("series", 0)
            hl_label = hl.get("label", "")
            if hl_idx is not None and hl_series < len(series_list):
                vals = series_list[hl_series].get("values", [])
                if hl_idx < len(vals):
                    pt = axes.c2p(hl_idx, float(vals[hl_idx]))
                    dot = Dot(pt, radius=0.1, color=RED_DOWN)
                    self.play(FadeIn(dot), run_time=0.15)
                    self.play(Indicate(dot, scale_factor=2, color="#FF1744"), run_time=0.4)
                    if hl_label:
                        hl_text = Text(hl_label, font_size=12, color=RED_DOWN, weight=BOLD)
                        hl_text.next_to(pt, UP, buff=0.2)
                        self.play(FadeIn(hl_text), run_time=0.2)

        # Legend
        if legend_items:
            legend_items.arrange(RIGHT, buff=0.5)
            legend_items.next_to(axes, DOWN, buff=0.5)
            self.play(FadeIn(legend_items), run_time=0.3)

        # Source label
        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''



# ── Horizontal bar chart ──────────────────────────────────────────────────



def _gen_horizontal_bar(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    source = data.get("source", "")
    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(labels))]

    return f'''from manim import *

class HorizontalBarScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        title = Text({json.dumps(title)}, font_size=30, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        labels = {json.dumps(labels)}
        values = {json.dumps(values)}
        colors = {json.dumps(colors)}
        source = {json.dumps(source)}

        if not values:
            self.wait(3)
            return

        max_val = max(values) or 1
        bar_height = min(0.5, 4.5 / max(len(labels), 1))
        bar_max_width = 8.0
        start_y = 2.0

        bars = VGroup()
        bar_rects = []
        for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
            y = start_y - i * (bar_height + 0.3)
            width = (val / max_val) * bar_max_width

            # Label on left
            label = Text(lbl, font_size=18, color="{TEXT_COLOR}")
            label.move_to(LEFT * 5.5 + UP * y)
            label.align_to(LEFT * 5.5, RIGHT)

            # Bar with rounded corners
            bar = RoundedRectangle(
                corner_radius=0.06,
                width=0.01, height=bar_height,
                color=col, fill_opacity=0.9, stroke_width=0,
            )
            bar.move_to(LEFT * 1.8 + UP * y, aligned_edge=LEFT)

            # Value label
            val_text = Text(f"{{val:,.0f}}", font_size=14, color=col, weight=BOLD)
            val_text.next_to(bar, RIGHT, buff=0.15)

            self.play(FadeIn(label), run_time=0.12)
            self.play(
                bar.animate.stretch_to_fit_width(max(width, 0.05)),
                run_time=0.35,
                rate_func=smooth,
            )
            val_text.next_to(bar, RIGHT, buff=0.15)
            self.play(FadeIn(val_text), run_time=0.12)
            bars.add(label, bar, val_text)
            bar_rects.append(bar)

        # Indicate the largest bar
        if values and bar_rects:
            max_idx = values.index(max(values))
            self.play(Indicate(bar_rects[max_idx], scale_factor=1.05, color="#FF1744"), run_time=0.5)

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''



# ── Grouped bar chart ────────────────────────────────────────────────────


def _gen_grouped_bar(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    series_list = data.get("series", [])
    title = instruction.get("title", "")
    source = data.get("source", "")

    if not series_list and "values" in data:
        series_list = [{"name": "Series", "values": data["values"]}]

    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(series_list))]

    return f'''from manim import *

class GroupedBarScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        title = Text({json.dumps(title)}, font_size=30, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        labels = {json.dumps(labels)}
        series_list = {json.dumps(series_list)}
        colors = {json.dumps(colors)}
        source = {json.dumps(source)}

        if not series_list or not labels:
            self.wait(3)
            return

        all_vals = [v for s in series_list for v in s.get("values", [])]
        max_val = max(all_vals) if all_vals else 10

        n_groups = len(labels)
        n_series = len(series_list)
        bar_w = min(0.4, 9.0 / (n_groups * n_series + n_groups))
        group_gap = bar_w * 0.5

        axes = Axes(
            x_range=[0, n_groups, 1],
            y_range=[0, max_val * 1.2, max_val * 0.25 or 1],
            x_length=10.5,
            y_length=5,
            axis_config={{"color": "#c0c0c0"}},
        )
        axes.next_to(title, DOWN, buff=0.35)
        self.play(Create(axes), run_time=0.5)

        # X-axis labels
        for i, lbl in enumerate(labels):
            t = Text(lbl, font_size=14, color="{MUTED}")
            t.next_to(axes.c2p(i + 0.5, 0), DOWN, buff=0.15)
            self.add(t)

        # Draw bars per group
        legend_items = VGroup()
        for g_idx in range(n_groups):
            for s_idx, series in enumerate(series_list):
                vals = series.get("values", [])
                if g_idx >= len(vals):
                    continue
                val = vals[g_idx]
                color = colors[s_idx % len(colors)]

                x_center = g_idx + 0.5
                x_offset = (s_idx - n_series / 2 + 0.5) * (bar_w + 0.05)
                bottom = axes.c2p(x_center + x_offset, 0)
                top = axes.c2p(x_center + x_offset, val)

                bar = Rectangle(
                    width=bar_w, height=abs(top[1] - bottom[1]),
                    color=color, fill_opacity=0.85, stroke_width=0,
                )
                bar.move_to((bottom + top) / 2)
                self.play(GrowFromEdge(bar, DOWN), run_time=0.15)

        # Legend
        for s_idx, series in enumerate(series_list):
            name = series.get("name", "")
            if name:
                dot = Dot(radius=0.06, color=colors[s_idx % len(colors)])
                lbl = Text(name, font_size=14, color="{TEXT_COLOR}")
                entry = VGroup(dot, lbl).arrange(RIGHT, buff=0.1)
                legend_items.add(entry)

        if legend_items:
            legend_items.arrange(RIGHT, buff=0.5)
            legend_items.next_to(axes, DOWN, buff=0.5)
            self.play(FadeIn(legend_items), run_time=0.3)

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''


# ── Donut chart ───────────────────────────────────────────────────────────



def _gen_donut_chart(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    center_value = data.get("center_value", "")
    center_label = data.get("center_label", "")
    source = data.get("source", "")
    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(labels))]

    return f'''from manim import *
import numpy as np

class DonutChartScene(Scene):
    def construct(self):
        self.camera.background_color = "{BG_DARK}"

        title = Text({json.dumps(title)}, font_size=30, color="{TEXT_COLOR}", weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        values = {json.dumps(values)}
        labels = {json.dumps(labels)}
        colors = {json.dumps(colors)}
        center_value = {json.dumps(str(center_value))}
        center_label = {json.dumps(center_label)}
        source = {json.dumps(source)}

        total = sum(values) or 1

        # Build donut sectors
        sectors = VGroup()
        start_angle = PI / 2
        for i, (val, col) in enumerate(zip(values, colors)):
            angle = (val / total) * TAU
            sector = AnnularSector(
                inner_radius=1.2, outer_radius=2.3,
                angle=angle, start_angle=start_angle,
                color=col, fill_opacity=0.95,
                stroke_color="{BG_DARK}", stroke_width=3,
            )
            sectors.add(sector)
            start_angle += angle

        sectors.move_to(LEFT * 1.5 + DOWN * 0.3)

        # Animate sectors with staggered reveal
        self.play(
            LaggedStart(*[GrowFromCenter(s) for s in sectors], lag_ratio=0.15),
            run_time=max(1.0, len(sectors) * 0.25),
        )

        # Center text
        if center_value:
            cv = Text(center_value, font_size=40, color="{TEXT_COLOR}", weight=BOLD)
            cv.move_to(sectors.get_center() + UP * 0.1)
            self.play(FadeIn(cv, scale=0.5), run_time=0.3)
        if center_label:
            cl = Text(center_label, font_size=16, color="{MUTED}")
            cl.move_to(sectors.get_center() + DOWN * 0.35)
            self.play(FadeIn(cl), run_time=0.2)

        # Legend on right side
        legend = VGroup()
        for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
            pct = val / total * 100
            dot = Dot(radius=0.08, color=col)
            text = Text(f"{{lbl}} ({{pct:.0f}}%)", font_size=16, color="{TEXT_COLOR}")
            entry = VGroup(dot, text).arrange(RIGHT, buff=0.15)
            legend.add(entry)

        legend.arrange(DOWN, buff=0.25, aligned_edge=LEFT)
        legend.move_to(RIGHT * 3.5 + DOWN * 0.3)
        self.play(FadeIn(legend), run_time=0.4)

        # Indicate the largest sector
        # Pause before highlighting the dominant sector
        if values:
            max_idx = values.index(max(values))
            self.wait(1.2)
            self.play(Indicate(sectors[max_idx], scale_factor=1.06, color="#FFD60A"), run_time=0.6)

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''



def _gen_pdf_forensic(instruction: dict) -> str:
    """Generate Manim code for the PDF Forensic effect."""
    from effects_catalog.templates.pdf_forensic import generate
    return generate(instruction)


def _gen_forensic_zoom(instruction: dict) -> str:
    """Generate Manim code for the Forensic Zoom effect."""
    from effects_catalog.templates.forensic_zoom import generate
    return generate(instruction)


def _gen_volatility_shadow(instruction: dict) -> str:
    """Generate Manim code for the Volatility Shadow effect."""
    from effects_catalog.templates.volatility_shadow import generate
    return generate(instruction)


def _gen_relative_velocity(instruction: dict) -> str:
    """Generate Manim code for the Relative Velocity effect."""
    from effects_catalog.templates.relative_velocity import generate
    return generate(instruction)


def _gen_contextual_heatmap(instruction: dict) -> str:
    """Generate Manim code for the Contextual Heatmap effect."""
    from effects_catalog.templates.contextual_heatmap import generate
    return generate(instruction)


def _gen_bull_bear_projection(instruction: dict) -> str:
    """Generate Manim code for the Bull vs Bear Projection effect."""
    from effects_catalog.templates.bull_bear_projection import generate
    return generate(instruction)


def _gen_moat_radar(instruction: dict) -> str:
    """Generate Manim code for the Moat Radar effect."""
    from effects_catalog.templates.moat_radar import generate
    return generate(instruction)


def _gen_atomic_reveal(instruction: dict) -> str:
    """Generate Manim code for the Atomic Reveal effect."""
    from effects_catalog.templates.atomic_reveal import generate
    return generate(instruction)


def _gen_liquidity_shock(instruction: dict) -> str:
    """Generate Manim code for the Liquidity Shock effect."""
    from effects_catalog.templates.liquidity_shock import generate
    return generate(instruction)


def _gen_momentum_glow(instruction: dict) -> str:
    """Generate Manim code for the Momentum Glow effect."""
    from effects_catalog.templates.momentum_glow import generate
    return generate(instruction)


def _gen_regime_shift(instruction: dict) -> str:
    """Generate Manim code for the Regime Shift effect."""
    from effects_catalog.templates.regime_shift import generate
    return generate(instruction)


def _gen_speed_ramp(instruction: dict) -> str:
    """Generate Manim code for the Speed Ramp effect."""
    from effects_catalog.templates.speed_ramp import generate
    return generate(instruction)


def _gen_capital_flow(instruction: dict) -> str:
    """Generate Manim code for the Capital Flow effect."""
    from effects_catalog.templates.capital_flow import generate
    return generate(instruction)


def _gen_compounding_explosion(instruction: dict) -> str:
    """Generate Manim code for the Compounding Explosion effect."""
    from effects_catalog.templates.compounding_explosion import generate
    return generate(instruction)


def _gen_market_share_territory(instruction: dict) -> str:
    """Generate Manim code for the Market Share Territory effect."""
    from effects_catalog.templates.market_share_territory import generate
    return generate(instruction)


def _gen_historical_rank(instruction: dict) -> str:
    """Generate Manim code for the Historical Rank effect."""
    from effects_catalog.templates.historical_rank import generate
    return generate(instruction)
