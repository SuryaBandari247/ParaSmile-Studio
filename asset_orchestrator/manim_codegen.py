"""Manim code generator — produces runnable Manim scene files from Visual_Instructions.

Generates Python source code with real Manim Scene subclasses that have
the instruction data baked in, so `manim render` can produce actual MP4s.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

BACKGROUND_COLOR = "#333333"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373",
    "#BA68C8", "#4DD0E1", "#AED581", "#FF8A65",
]


def generate_scene_code(instruction: dict) -> str:
    """Generate a complete Manim Python file for the given instruction."""
    vis_type = instruction.get("type", "text_overlay")
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
    }
    gen = generators.get(vis_type, _gen_text_overlay)
    return gen(instruction)


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

        chart = BarChart(
            values=values,
            bar_names=labels,
            bar_colors=colors,
            y_range=[0, max(values) * 1.2 if values else 10, max(values) * 0.2 if values else 2],
            x_length=10,
            y_length=5,
        )
        chart.next_to(title, DOWN, buff=0.4)

        # Progressive bar reveal — bars grow one by one
        self.play(Create(chart.get_axes()), run_time=0.5)
        for bar in chart.bars:
            self.play(GrowFromEdge(bar, DOWN), run_time=0.2)

        # Value labels on top of bars
        value_labels = VGroup()
        for i, (bar, val) in enumerate(zip(chart.bars, values)):
            lbl = Text(f"{{val:,.0f}}", font_size=14, color=colors[i % len(colors)], weight=BOLD)
            lbl.next_to(bar, UP, buff=0.1)
            value_labels.add(lbl)
        self.play(FadeIn(value_labels), run_time=0.3)

        # Indicate the highest bar
        if values:
            max_idx = values.index(max(values))
            self.play(Indicate(chart.bars[max_idx], scale_factor=1.1, color="#ff6b6b"), run_time=0.4)

        # Indicate specific highlights
        for hl in highlights:
            idx = hl.get("index")
            if idx is not None and idx < len(chart.bars):
                self.play(Indicate(chart.bars[idx], scale_factor=1.1, color="#ff6b6b"), run_time=0.3)

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
            axis_config={{"color": "#555555"}},
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

BG_DARK = "#1a1a2e"
ACCENT_RED = "#e94560"
ACCENT_BLUE = "#0f3460"
REDDIT_ORANGE = "#FF4500"
REDDIT_BG = "#1A1A1B"
REDDIT_CARD = "#272729"
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
        title = Text({json.dumps(post_title)}, font_size=28, color="#D7DADC", line_spacing=1.3)
        title.move_to(ORIGIN)
        if title.width > 10:
            title.scale_to_fit_width(10)
        self.play(FadeIn(title, shift=UP * 0.2), run_time=0.5)

        # Vote bar on left
        up_arrow = Triangle(color="{REDDIT_ORANGE}", fill_opacity=1).scale(0.15)
        up_arrow.move_to(LEFT * 5.2 + DOWN * 0.5)
        vote_count = Text({json.dumps(str(upvotes))}, font_size=20, color="#D7DADC", weight=BOLD)
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
        label = Text({json.dumps(label)}, font_size=36, color="#FFFFFF", weight=BOLD)
        label.next_to(stat, DOWN, buff=0.4)

        # Subtitle
        subtitle = Text({json.dumps(subtitle)}, font_size=22, color="{MUTED}")
        subtitle.next_to(label, DOWN, buff=0.3)

        # Dramatic entrance
        self.play(GrowFromCenter(stat), run_time=0.6)
        self.play(FadeIn(label, shift=UP * 0.2), run_time=0.4)
        if {json.dumps(subtitle.strip() != "")}:
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
        quote = Text({json.dumps(quote)}, font_size=28, color="#FFFFFF", line_spacing=1.4)
        quote.move_to(RIGHT * 0.3 + UP * 0.3)
        if quote.width > 9:
            quote.scale_to_fit_width(9)

        # Attribution
        attr = Text({json.dumps("— " + attribution if attribution else "")}, font_size=20, color="{MUTED}", slant=ITALIC)
        attr.next_to(quote, DOWN, buff=0.5)
        attr.align_to(quote, LEFT)

        self.play(FadeIn(bar), run_time=0.3)
        self.play(FadeIn(quote, shift=RIGHT * 0.3), run_time=0.6)
        if {json.dumps(bool(attribution))}:
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
        heading = Text({json.dumps(heading)}, font_size=52, color="#FFFFFF", weight=BOLD)
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
        heading = Text({json.dumps(heading)}, font_size=36, color="#FFFFFF", weight=BOLD)
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
            text = Text(bullet_text, font_size=24, color="#D7DADC", line_spacing=1.2)
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
        title = Text({json.dumps(title)}, font_size=32, color="#FFFFFF", weight=BOLD)
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
            t = Text("• " + item, font_size=20, color="#D7DADC")
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
            t = Text("• " + item, font_size=20, color="#D7DADC")
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
            before = Text(parts[0], font_size=42, color="#FFFFFF")
            emph = Text(emphasis, font_size=42, color="{ACCENT_RED}", weight=BOLD)
            after = Text(parts[1] if len(parts) > 1 else "", font_size=42, color="#FFFFFF")
            group = VGroup(before, emph, after).arrange(RIGHT, buff=0.1)
        else:
            group = Text(statement, font_size=42, color="#FFFFFF", line_spacing=1.3)

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
    Returns enriched copy of data dict.
    """
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
            logger.info(
                "Enriched chart with Yahoo Finance: %d tickers, %d points",
                len(series_list), len(all_dates),
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
    # Highlight points: [{"index": 5, "label": "Export ban"}]
    highlights = data.get("highlights", [])

    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(series_list))]

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
        is_pct = {json.dumps(is_pct)}
        source = {json.dumps(source)}
        events = {json.dumps(events)}
        highlights = {json.dumps(highlights)}

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
            axis_config={{"color": "#555555", "include_ticks": True}},
        )
        axes.next_to(title, DOWN, buff=0.35)

        # X-axis date labels
        step = max(1, n // 6)
        x_labels = VGroup()
        for i in range(0, n, step):
            if i < len(dates):
                lbl = Text(dates[i][:7], font_size=12, color="{MUTED}")
                lbl.next_to(axes.c2p(i, y_min), DOWN, buff=0.15)
                x_labels.add(lbl)

        chart_group = VGroup(axes, x_labels)
        self.play(Create(axes), FadeIn(x_labels), run_time=0.6)

        # Zero line for pct_change
        if is_pct and y_min < 0:
            zero_line = DashedLine(
                axes.c2p(0, 0), axes.c2p(n - 1, 0),
                color="#666666", stroke_width=1,
            )
            self.play(Create(zero_line), run_time=0.2)
            chart_group.add(zero_line)

        # Zoom camera into chart area for the draw phase
        self.play(
            self.camera.frame.animate.set(width=13).move_to(axes.get_center()),
            run_time=0.5,
        )

        # Draw each series with camera tracking
        all_lines = VGroup()
        all_badges = VGroup()
        legend_items = VGroup()

        for idx, series in enumerate(series_list):
            vals = [float(v) for v in series.get("values", [])][:n]
            color = colors[idx % len(colors)]
            name = series.get("name", "")

            points = [axes.c2p(i, v) for i, v in enumerate(vals)]
            line = VMobject(color=color, stroke_width=3)
            line.set_points_smoothly(points)

            # Animated draw with camera following the line endpoint
            # Split into segments for camera tracking effect
            segments = min(4, max(2, n // 10))
            seg_size = len(points) // segments
            for seg_i in range(segments):
                start_idx = seg_i * seg_size
                end_idx = min((seg_i + 1) * seg_size + 1, len(points))
                if start_idx >= end_idx:
                    break
                seg_points = points[start_idx:end_idx]
                seg_line = VMobject(color=color, stroke_width=3)
                seg_line.set_points_smoothly(seg_points)

                # Camera gently tracks the drawing
                target_point = seg_points[-1]
                self.play(
                    Create(seg_line),
                    self.camera.frame.animate.move_to(
                        axes.get_center() * 0.6 + np.array(target_point) * 0.4
                    ),
                    run_time=0.4,
                )
                all_lines.add(seg_line)

            # End-of-line value badge
            end_val = vals[-1]
            if is_pct:
                badge_text = f"+{{end_val:.1f}}%" if end_val >= 0 else f"{{end_val:.1f}}%"
            else:
                badge_text = f"${{end_val:,.0f}}" if end_val > 100 else f"{{end_val:,.2f}}"

            badge = Text(badge_text, font_size=16, color=color, weight=BOLD)
            badge.next_to(points[-1], RIGHT, buff=0.15)
            self.play(FadeIn(badge), run_time=0.2)
            all_badges.add(badge)

            # Legend entry
            if name:
                dot = Dot(radius=0.06, color=color)
                lbl = Text(name, font_size=14, color="{TEXT_COLOR}")
                entry = VGroup(dot, lbl).arrange(RIGHT, buff=0.1)
                legend_items.add(entry)

        # Restore camera to full view
        self.play(Restore(self.camera.frame), run_time=0.5)

        # Event markers — vertical dashed lines with labels
        for evt in events:
            evt_idx = evt.get("index")
            evt_label = evt.get("label", "")
            if evt_idx is not None and 0 <= evt_idx < n:
                marker = DashedLine(
                    axes.c2p(evt_idx, y_min),
                    axes.c2p(evt_idx, y_max * 0.95),
                    color="#ef4444", stroke_width=1.5, dash_length=0.1,
                )
                marker_label = Text(evt_label, font_size=11, color="#ef4444", weight=BOLD)
                marker_label.next_to(axes.c2p(evt_idx, y_max * 0.9), UP, buff=0.1)
                if marker_label.width > 2.5:
                    marker_label.scale_to_fit_width(2.5)
                self.play(Create(marker), FadeIn(marker_label), run_time=0.3)

        # Indicate highlights — pulse specific data points
        for hl in highlights:
            hl_idx = hl.get("index")
            hl_series = hl.get("series", 0)
            hl_label = hl.get("label", "")
            if hl_idx is not None and hl_series < len(series_list):
                vals = series_list[hl_series].get("values", [])
                if hl_idx < len(vals):
                    pt = axes.c2p(hl_idx, float(vals[hl_idx]))
                    dot = Dot(pt, radius=0.1, color="#ef4444")
                    self.play(FadeIn(dot), run_time=0.15)
                    self.play(Indicate(dot, scale_factor=2, color="#ff6b6b"), run_time=0.4)
                    if hl_label:
                        hl_text = Text(hl_label, font_size=12, color="#ef4444", weight=BOLD)
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
        for i, (lbl, val, col) in enumerate(zip(labels, values, colors)):
            y = start_y - i * (bar_height + 0.25)
            width = (val / max_val) * bar_max_width

            # Label on left
            label = Text(lbl, font_size=18, color="{TEXT_COLOR}")
            label.move_to(LEFT * 5.5 + UP * y)
            label.align_to(LEFT * 5.5, RIGHT)

            # Bar
            bar = Rectangle(
                width=0.01, height=bar_height,
                color=col, fill_opacity=0.85, stroke_width=0,
            )
            bar.move_to(LEFT * 1.8 + UP * y, aligned_edge=LEFT)

            # Value label
            val_text = Text(f"{{val:,.0f}}", font_size=14, color=col, weight=BOLD)
            val_text.next_to(bar, RIGHT, buff=0.15)

            self.play(FadeIn(label), run_time=0.15)
            self.play(
                bar.animate.stretch_to_fit_width(max(width, 0.05)),
                run_time=0.4,
            )
            val_text.next_to(bar, RIGHT, buff=0.15)
            self.play(FadeIn(val_text), run_time=0.15)
            bars.add(label, bar, val_text)

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
            axis_config={{"color": "#555555"}},
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
                color=col, fill_opacity=0.9,
                stroke_color="#1a1a2e", stroke_width=3,
            )
            sectors.add(sector)
            start_angle += angle

        sectors.move_to(LEFT * 1.5 + DOWN * 0.3)

        # Animate sectors one by one
        for sector in sectors:
            self.play(Create(sector), run_time=0.3)

        # Center text
        if center_value:
            cv = Text(center_value, font_size=36, color="{TEXT_COLOR}", weight=BOLD)
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

        if source:
            src = Text(f"Source: {{source}}", font_size=12, color="{MUTED}")
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''
