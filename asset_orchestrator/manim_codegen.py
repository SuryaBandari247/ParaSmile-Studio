"""Manim code generator — produces runnable Manim scene files from Visual_Instructions.

Generates Python source code with real Manim Scene subclasses that have
the instruction data baked in, so `manim render` can produce actual MP4s.
"""

from __future__ import annotations

import json

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
    colors = [ACCENT_COLORS[i % len(ACCENT_COLORS)] for i in range(len(labels))]
    return f'''from manim import *

class BarChartScene(Scene):
    def construct(self):
        self.camera.background_color = "{BACKGROUND_COLOR}"
        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}")
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        labels = {json.dumps(labels)}
        values = {json.dumps(values)}
        colors = {json.dumps(colors)}

        chart = BarChart(
            values=values,
            bar_names=labels,
            bar_colors=colors,
            y_range=[0, max(values) * 1.2 if values else 10, max(values) * 0.2 if values else 2],
            x_length=10,
            y_length=5,
        )
        chart.next_to(title, DOWN, buff=0.4)
        self.play(Create(chart), run_time=1.5)
        self.wait(3)
        self.play(FadeOut(chart), FadeOut(title), run_time=0.5)
'''


def _gen_line_chart(instruction: dict) -> str:
    data = instruction.get("data", {})
    labels = data.get("labels", [])
    values = data.get("values", [])
    title = instruction.get("title", "")
    return f'''from manim import *
import numpy as np

class LineChartScene(Scene):
    def construct(self):
        self.camera.background_color = "{BACKGROUND_COLOR}"
        title = Text({json.dumps(title)}, font_size=32, color="{TEXT_COLOR}")
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title), run_time=0.4)

        values = {json.dumps(values)}
        labels = {json.dumps(labels)}

        axes = Axes(
            x_range=[0, len(values), 1],
            y_range=[0, max(values) * 1.2 if values else 10, max(values) * 0.2 if values else 2],
            x_length=10,
            y_length=5,
            axis_config={{"color": "{TEXT_COLOR}"}},
        )
        axes.next_to(title, DOWN, buff=0.4)

        points = [axes.c2p(i, v) for i, v in enumerate(values)]
        line = VMobject(color="{ACCENT_COLORS[0]}")
        line.set_points_smoothly(points)

        dots = VGroup(*[Dot(p, color="{ACCENT_COLORS[1]}") for p in points])

        self.play(Create(axes), run_time=0.8)
        self.play(Create(line), run_time=1.5)
        self.play(FadeIn(dots), run_time=0.5)
        self.wait(3)
        self.play(FadeOut(axes), FadeOut(line), FadeOut(dots), FadeOut(title), run_time=0.5)
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
