"""Liquidity Shock (Simple) — clean line chart with shockwave pulse.

White-background editorial-layout timeseries with vertical flash line,
camera shake, shock dot, and narrative ending overlay.
Use this for quick explainers where a simple line chart is clearer
than a full candlestick terminal view.

For the advanced TradingView terminal version, see liquidity_shock_terminal.py.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

SCENE_CLASS = "LiquidityShockSimpleScene"


class DateRangeError(Exception):
    def __init__(self, shock_date: str, valid_start: str, valid_end: str):
        self.shock_date = shock_date
        self.valid_start = valid_start
        self.valid_end = valid_end
        super().__init__(
            f"shock_date '{shock_date}' outside data range ({valid_start} to {valid_end})"
        )


class RangeError(Exception):
    def __init__(self, value: float, field: str):
        self.value = value
        self.field = field
        super().__init__(f"{field} value {value} is outside valid range")


def generate(instruction: dict) -> str:  # noqa: C901
    """Generate Manim code for the Liquidity Shock effect."""
    data = instruction.get("data", {})
    shock_date = data.get("shock_date", "")
    shock_color = data.get("shock_color", "#EF4444")
    shock_intensity = data.get("shock_intensity", 0.7)
    shock_label = data.get("shock_label", "")
    shock_caption = data.get("shock_caption", "")
    title = instruction.get("title", "")
    subtitle = data.get("subtitle", "")
    source = data.get("source", "")
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])
    unit = data.get("unit", "$")

    # Documentary palette
    line_color = data.get("line_color", "#2563EB")
    accent_pos = "#10B981"
    accent_neg = "#EF4444"
    smk_text = "#C2410C"
    smk_border = "#F97316"
    txt_pri = "#111827"
    txt_sec = "#374151"
    txt_mut = "#6B7280"
    ax_col = "#9CA3AF"
    grd_col = "#E5E7EB"

    _caption = shock_caption if shock_caption else subtitle

    # Build code as list of lines for readability
    J = json.dumps  # shorthand

    code = f'''from manim import *
import numpy as np

FONT = "Inter"

class {SCENE_CLASS}(MovingCameraScene):
    """Editorial-layout timeseries with vertical energy pulse at event date."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"
        self.camera.frame.save_state()

        shock_date = {J(shock_date)}
        shock_color = {J(shock_color)}
        shock_intensity = {J(shock_intensity)}
        shock_label = {J(shock_label)}
        shock_caption = {J(_caption)}
        title = {J(title)}
        subtitle = {J(subtitle)}
        source = {J(source)}
        unit = {J(unit)}
        dates = {J(dates)}
        values = {J(values)}
        series = {J(series)}

        LC = {J(line_color)}
        AP = {J(accent_pos)}
        AN = {J(accent_neg)}
        TP = {J(txt_pri)}
        TS = {J(txt_sec)}
        TM = {J(txt_mut)}
        AC = {J(ax_col)}
        GC = {J(grd_col)}
        SMT = {J(smk_text)}
        SMB = {J(smk_border)}

        if series and not values:
            s = series[0]
            pts = s.get("data", s.get("points", []))
            dates = [p.get("date", "") for p in pts]
            values = [p.get("value", p.get("close", 0)) for p in pts]

        if len(values) < 2:
            err = Text("Insufficient data", font=FONT, font_size=28, color=shock_color)
            self.play(FadeIn(err))
            self.wait(3)
            return

        n = len(values)
        y_min = min(values) * 0.92
        y_max = max(values) * 1.08
        y_step = (y_max - y_min) / 5

        # ══ EDITORIAL LAYOUT ══
        # Chart occupies ~70% of screen, pushed down for title breathing room
        axes = Axes(
            x_range=[0, n - 1, max(1, n // 6)],
            y_range=[y_min, y_max, y_step],
            x_length=11, y_length=4.5,
            axis_config={{"color": AC, "stroke_width": 1.5, "include_ticks": True}},
            tips=False,
        )
        axes.move_to(DOWN * 0.55 + RIGHT * 0.15)

        # ── Title — top-left, large, editorial ──
        title_mob = None
        if title:
            title_mob = Text(title, font=FONT, font_size=44, color=TP, weight=BOLD)
            title_mob.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_mob.width > 12:
                title_mob.scale_to_fit_width(12)
            self.play(FadeIn(title_mob, shift=DOWN * 0.1), run_time=0.4)

        # ── Subtitle — below title, left-aligned (will turn red as payoff) ──
        sub_mob = None
        if subtitle:
            sub_mob = Text(subtitle, font=FONT, font_size=22, color=TS)
            sub_ref = title_mob if title_mob else axes
            sub_mob.next_to(sub_ref, DOWN, buff=0.15, aligned_edge=LEFT)
            if sub_mob.width > 12:
                sub_mob.scale_to_fit_width(12)
            self.play(FadeIn(sub_mob, shift=DOWN * 0.05), run_time=0.3)

        # ── Grid — major only, soft ──
        grid = VGroup()
        for i in range(1, 6):
            y_val = y_min + i * y_step
            if y_val <= y_max:
                gl = Line(
                    axes.c2p(0, y_val), axes.c2p(n - 1, y_val),
                    color=GC, stroke_width=1, stroke_opacity=0.6,
                )
                grid.add(gl)

        # ── X-axis date labels — clean, 3-5 key dates, no rotation ──
        x_labels = VGroup()
        # Pick key indices: first, shock, last, plus 1-2 evenly spaced
        key_indices = [0, n - 1]
        _si = n // 2
        if shock_date and dates:
            for _i, _d in enumerate(dates):
                if _d == shock_date or _d.startswith(shock_date):
                    _si = _i
                    break
        if _si not in key_indices:
            key_indices.append(_si)
        # Add 1-2 midpoints for context
        for frac in [0.33, 0.66]:
            mid = int(n * frac)
            if all(abs(mid - k) > n * 0.12 for k in key_indices):
                key_indices.append(mid)
        key_indices = sorted(set(key_indices))

        import datetime as _dt
        _MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        for ki in key_indices:
            if ki < len(dates) and dates[ki]:
                raw = dates[ki][:10]
                # Format: "Oct 15" or "Jul 2024"
                try:
                    dp = _dt.datetime.strptime(raw, "%Y-%m-%d")
                    if ki == _si:
                        fmt_d = f"{{_MONTHS[dp.month-1]}} {{dp.day}}"
                    else:
                        fmt_d = f"{{_MONTHS[dp.month-1]}} {{dp.year}}" if ki in [0, n-1] else f"{{_MONTHS[dp.month-1]}}"
                except Exception:
                    fmt_d = raw
                lbl = Text(fmt_d, font=FONT, font_size=16, color=TM)
                lbl.next_to(axes.c2p(ki, y_min), DOWN, buff=0.2)
                x_labels.add(lbl)

        # ── Y-axis price labels ──
        y_labels = VGroup()
        for i in range(6):
            y_val = y_min + i * y_step
            if unit == "$":
                fmt = f"${{y_val:,.0f}}"
            elif unit == "%":
                fmt = f"{{y_val:.1f}}%"
            else:
                fmt = f"{{y_val:,.0f}}"
            lbl = Text(fmt, font=FONT, font_size=16, color=TM)
            lbl.next_to(axes.c2p(0, y_val), LEFT, buff=0.18)
            y_labels.add(lbl)

        self.play(Create(axes), FadeIn(grid), FadeIn(x_labels), FadeIn(y_labels), run_time=0.5)

        # ── Find shock + trough + peak indices (needed for segmented line) ──
        shock_idx = n // 2
        if shock_date and dates:
            for i, d in enumerate(dates):
                if d == shock_date or d.startswith(shock_date):
                    shock_idx = i
                    break
        # Find trough: local minimum in the window around/after shock
        trough_idx = shock_idx
        for _ti in range(max(0, shock_idx - 2), min(shock_idx + 15, n)):
            if values[_ti] <= values[trough_idx]:
                trough_idx = _ti
        if trough_idx == shock_idx:
            trough_idx = min(shock_idx + 1, n - 1)
        # Find cliff start: walk backward from shock_idx to find where
        # the steep drop begins. We want only the dramatic cliff in red,
        # not the gradual drift. Use the biggest single-step drop as anchor
        # and extend back only while drops stay steep (> 50% of max drop).
        max_drop = 0
        for _ci in range(max(1, shock_idx - 5), shock_idx + 1):
            step_drop = values[_ci - 1] - values[_ci]
            if step_drop > max_drop:
                max_drop = step_drop
        steep_thresh = max_drop * 0.35 if max_drop > 0 else 0
        cliff_start = shock_idx
        for _ci in range(shock_idx, max(0, shock_idx - 6), -1):
            step_drop = values[_ci - 1] - values[_ci] if _ci > 0 else 0
            if step_drop >= steep_thresh:
                cliff_start = _ci
            else:
                break
        # cliff_start is the first index of the steep section;
        # the blue line runs up to the point just before it
        peak_idx = max(0, cliff_start - 1) if cliff_start > 0 else 0

        # ── Price line — 3 segments: blue / red decline / blue recovery ──
        points = [axes.c2p(i, v) for i, v in enumerate(values)]

        # Area fill under entire line
        area_pts = points + [axes.c2p(n - 1, y_min), axes.c2p(0, y_min)]
        area_top = Polygon(*area_pts, color=LC, fill_opacity=0.10, stroke_width=0)
        self.add(area_top)

        # Segment 1: pre-crash (blue) — index 0 to peak_idx (inclusive)
        pre_pts = [axes.c2p(i, values[i]) for i in range(0, peak_idx + 1)]
        line_pre = VMobject(color=LC, stroke_width=6)
        if len(pre_pts) >= 2:
            line_pre.set_points_smoothly(pre_pts)

        # Segment 2: decline (red) — peak_idx to trough_idx (inclusive)
        decline_pts = [axes.c2p(i, values[i]) for i in range(peak_idx, trough_idx + 1)]
        line_decline = VMobject(color=shock_color, stroke_width=6)
        if len(decline_pts) >= 2:
            line_decline.set_points_smoothly(decline_pts)

        # Segment 3: recovery (blue) — trough_idx to end (inclusive)
        post_pts = [axes.c2p(i, values[i]) for i in range(trough_idx, n)]
        line_post = VMobject(color=LC, stroke_width=6)
        if len(post_pts) >= 2:
            line_post.set_points_smoothly(post_pts)

        # Draw pre-crash segment with camera tracking
        draw_time = min(2.0, max(0.8, n * 0.006))
        self.play(
            Create(line_pre),
            self.camera.frame.animate.set(width=14).move_to(axes.get_center()),
            run_time=draw_time * 0.6,
            rate_func=smooth,
        )
        # Draw decline + recovery quickly (they appear during/after shock)
        self.play(Create(line_decline), run_time=draw_time * 0.15)
        self.play(Create(line_post), run_time=draw_time * 0.25)

        # Reference for glow/badge — combine all segments
        line = VGroup(line_pre, line_decline, line_post)

        # ── Multi-layer glow — cinematic depth ──
        glow1 = line_pre.copy().set_stroke(color=LC, width=18, opacity=0.08)
        glow2 = line_pre.copy().set_stroke(color=LC, width=30, opacity=0.04)
        self.add(glow2, glow1)

        # ── End-of-line value badge ──
        end_val = values[-1]
        if unit == "$":
            badge_text = f"${{end_val:,.0f}}" if end_val > 100 else f"${{end_val:.2f}}"
        elif unit == "%":
            badge_text = f"{{end_val:.1f}}%"
        else:
            badge_text = f"{{end_val:,.0f}}"
        badge_color = AP if values[-1] >= values[0] else AN
        badge_bg = RoundedRectangle(
            corner_radius=0.1, width=1.8, height=0.4,
            color=badge_color, fill_opacity=0.1, stroke_width=1.2, stroke_color=badge_color,
        )
        badge_label = Text(badge_text, font=FONT, font_size=18, color=badge_color, weight=BOLD)
        badge = VGroup(badge_bg, badge_label)
        badge_label.move_to(badge_bg.get_center())
        badge.next_to(points[-1], RIGHT, buff=0.15)
        self.play(FadeIn(badge, scale=0.8), run_time=0.2)

        self.play(Restore(self.camera.frame), run_time=0.3)

        shock_x = axes.c2p(shock_idx, 0)[0]
        shock_y = axes.c2p(0, values[shock_idx])[1]
        shock_pt = axes.c2p(shock_idx, values[shock_idx])

        # ── Camera zooms into shock region ──
        axes_bottom = axes.c2p(0, y_min)[1] - 0.8
        axes_top = axes.c2p(0, y_max)[1] + 0.3
        zoom_h = axes_top - axes_bottom
        zoom_cy = (axes_top + axes_bottom) / 2
        zoom_center = np.array([shock_x, zoom_cy, 0])
        self.play(
            self.camera.frame.animate.set(width=8, height=zoom_h).move_to(zoom_center),
            run_time=0.4,
        )

        # ══ SHOCK EFFECT ══

        # 1. Flash line at crash date
        flash = Line(
            axes.c2p(shock_idx, y_min), axes.c2p(shock_idx, y_max),
            color=shock_color, stroke_width=4, stroke_opacity=0.9,
        )
        flash_glow = flash.copy().set_stroke(color=shock_color, width=12, opacity=0.3)
        self.play(Create(flash), FadeIn(flash_glow), run_time=0.1)

        # 2. Camera micro-shake
        shake_amt = shock_intensity * 0.12
        orig_pos = self.camera.frame.get_center().copy()
        for _ in range(3):
            offset = np.array([
                np.random.uniform(-shake_amt, shake_amt),
                np.random.uniform(-shake_amt, shake_amt),
                0,
            ])
            self.camera.frame.move_to(orig_pos + offset)
            self.wait(0.05)
        self.camera.frame.move_to(orig_pos)

        # 3. Flash fade out
        self.play(FadeOut(flash), FadeOut(flash_glow), run_time=0.4)

        # ══ NEWS-STYLE SHOCK ANNOTATION ══
        if shock_label:
            # Split label into lines if " — " separator exists
            parts = shock_label.split(" — ") if " — " in shock_label else [shock_label]

            ann_lines = VGroup()
            for idx_p, part in enumerate(parts):
                sz = 18 if idx_p == 0 else 16
                wt = BOLD if idx_p == 0 else NORMAL
                t = Text(part.strip(), font=FONT, font_size=sz, color=SMT if idx_p == 0 else TS, weight=wt)
                ann_lines.add(t)
            ann_lines.arrange(DOWN, buff=0.06, aligned_edge=LEFT)

            # Horizontal rule above and below
            rule_w = max(ann_lines.width, 2.0) + 0.3
            rule_top = Line(LEFT * rule_w / 2, RIGHT * rule_w / 2, color=SMB, stroke_width=2)
            rule_bot = rule_top.copy()
            rule_top.next_to(ann_lines, UP, buff=0.08)
            rule_bot.next_to(ann_lines, DOWN, buff=0.08)

            ann_group = VGroup(rule_top, ann_lines, rule_bot)
            # Place above shock point — enough to clear the line but stay in zoomed frame
            ann_group.next_to(shock_pt, UP, buff=0.45)

            self.play(FadeIn(ann_group, shift=DOWN * 0.1), run_time=0.4)

        # Shock dot with indicate
        shock_dot = Dot(shock_pt, radius=0.09, color=shock_color)
        self.play(FadeIn(shock_dot), run_time=0.2)
        self.play(Indicate(shock_dot, color=shock_color, scale_factor=1.6), run_time=0.5)

        # Hold on zoomed shock
        self.wait(1.0)

        # ══ NARRATIVE ENDING — subtitle turns red as payoff ══
        self.play(Restore(self.camera.frame), run_time=0.5)

        if sub_mob is not None:
            # Create red version at same position
            sub_red = Text(subtitle, font=FONT, font_size=22, color=AN, weight=BOLD)
            sub_red.move_to(sub_mob.get_center())
            if sub_red.width > 12:
                sub_red.scale_to_fit_width(12)
            self.play(FadeOut(sub_mob, run_time=0.2))
            self.play(FadeIn(sub_red, run_time=0.4))
            self.wait(2.0)
        else:
            self.wait(2.0)

        # ── Source attribution ──
        if source:
            src = Text(f"Source: {{source}}", font=FONT, font_size=14, color=TM)
            src.to_edge(DOWN, buff=0.15).to_edge(RIGHT, buff=0.3)
            self.play(FadeIn(src), run_time=0.2)

        self.wait(1.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
'''

    return code
