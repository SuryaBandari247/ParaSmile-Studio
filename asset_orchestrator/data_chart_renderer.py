"""Data Chart Renderer — produces broadcast-quality animated chart videos.

Style reference: modern finance infographic (light bg, bold title with accent
bar, smooth thick lines, end-of-line value badges, minimal axes).

Uses matplotlib for frame generation, FFmpeg for stitching.
Supports: bar, line, area, grouped_bar, horizontal_bar, pie, donut, timeseries.

When chart data includes a `ticker` or `tickers` field, the renderer can
optionally fetch live price history from Yahoo Finance via yfinance.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

logger = logging.getLogger(__name__)

# ── Theme ──────────────────────────────────────────────────────────────────

BG_COLOR = "#e8ecf1"       # light blue-gray canvas
CARD_COLOR = "#e8ecf1"     # same as bg (no card border)
GRID_COLOR = "#d0d5de"
AXIS_COLOR = "#b0b8c8"
TEXT_COLOR = "#1a1f36"      # near-black for titles
MUTED_TEXT = "#5a6478"      # axis labels, subtitles
SUBTITLE_COLOR = "#6b7a8d"
SOURCE_COLOR = "#8896a6"

ACCENT_BAR_COLOR = "#2563eb"  # blue accent bar next to title

PALETTE = [
    "#2563eb",  # blue
    "#f59e0b",  # amber/orange
    "#10b981",  # teal/emerald
    "#ef4444",  # red
    "#8b5cf6",  # violet
    "#06b6d4",  # cyan
    "#ec4899",  # pink
    "#84cc16",  # lime
]

GRADIENT_PAIRS = [
    ("#2563eb", "#93c5fd"),
    ("#f59e0b", "#fde68a"),
    ("#10b981", "#6ee7b7"),
    ("#ef4444", "#fca5a5"),
    ("#8b5cf6", "#c4b5fd"),
    ("#06b6d4", "#67e8f9"),
    ("#ec4899", "#f9a8d4"),
    ("#84cc16", "#d9f99d"),
]


# ── Font setup ─────────────────────────────────────────────────────────────

_FONT_LOADED = False

def _load_fonts() -> None:
    global _FONT_LOADED
    if _FONT_LOADED:
        return
    _FONT_LOADED = True
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [
            "Inter", "SF Pro Display", "Helvetica Neue",
            "Arial", "DejaVu Sans",
        ],
        "font.weight": "normal",
        "axes.unicode_minus": False,
    })


# ── Theme helpers ──────────────────────────────────────────────────────────

def _apply_theme(ax: plt.Axes, fig: plt.Figure, axis_alpha: float = 1.0) -> None:
    """Apply clean light finance theme. axis_alpha animates axis construction."""
    _load_fonts()
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(CARD_COLOR)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.tick_params(
        colors=MUTED_TEXT, labelsize=11, length=0, pad=6,
    )
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_alpha(axis_alpha)

    ax.xaxis.label.set_color(MUTED_TEXT)
    ax.yaxis.label.set_color(MUTED_TEXT)
    ax.grid(True, axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.6 * axis_alpha)
    ax.set_axisbelow(True)


def _draw_title_block(fig: plt.Figure, title: str, subtitle: str = "",
                      source_label: str = "", alpha: float = 1.0) -> None:
    """Draw the bold title with left accent bar, subtitle, and source."""
    # Accent bar (thick vertical blue line left of title)
    from matplotlib.patches import Rectangle
    bar = Rectangle(
        (0.04, 0.88), 0.012, 0.08,
        facecolor=ACCENT_BAR_COLOR, alpha=alpha,
        transform=fig.transFigure, zorder=10,
    )
    fig.patches.append(bar)

    # Title — large, bold, dark
    fig.text(
        0.065, 0.94, title,
        fontsize=26, fontweight="bold", color=TEXT_COLOR,
        va="top", ha="left", alpha=alpha,
        transform=fig.transFigure,
    )

    # Subtitle
    if subtitle:
        fig.text(
            0.065, 0.875, subtitle,
            fontsize=13, color=SUBTITLE_COLOR,
            va="top", ha="left", alpha=alpha * 0.85,
            transform=fig.transFigure,
        )

    # Source — bottom left
    if source_label:
        fig.text(
            0.05, 0.025, f"Source: {source_label}",
            fontsize=10, color=SOURCE_COLOR,
            va="bottom", ha="left", alpha=alpha * 0.6,
            transform=fig.transFigure,
        )


def _format_value(val: float) -> str:
    """Format large numbers with K/M/B suffixes."""
    if abs(val) >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.1f}K"
    return f"${val:.0f}"


def _format_pct(val: float) -> str:
    """Format as percentage with sign."""
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


# ── Animation phase helpers ────────────────────────────────────────────────

def _axis_progress(progress: float) -> float:
    """Axis construction: 0→0.12 of timeline."""
    return min(1.0, progress / 0.12)

def _data_progress(progress: float) -> float:
    """Data reveal: 0.08→0.82."""
    return max(0.0, min(1.0, (progress - 0.08) / 0.74))

def _label_progress(progress: float) -> float:
    """Labels/badges fade in: 0.55→0.85."""
    return max(0.0, min(1.0, (progress - 0.55) / 0.30))


# ── Yahoo Finance data enrichment ──────────────────────────────────────────

def _enrich_from_yahoo(data: dict) -> dict:
    """If data has `ticker`/`tickers` + `period`, fetch live price history.

    Merges fetched data into the chart data dict so the renderer can use it.
    Only runs when the data doesn't already have `values`/`series` populated.
    """
    tickers = data.get("tickers") or []
    single = data.get("ticker", "")
    if single and single not in tickers:
        tickers = [single] + tickers
    if not tickers:
        return data

    # Skip if data already has values
    has_values = bool(data.get("values")) or bool(data.get("series"))
    if has_values:
        return data

    period = data.get("period", "1y")
    interval = data.get("interval", "1wk")
    value_type = data.get("value_type", "close")  # close, pct_change

    try:
        import yfinance as yf

        series_list = []
        all_dates = None

        for symbol in tickers[:5]:  # cap at 5 tickers
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

            series_list.append({
                "name": symbol,
                "values": values,
            })

        if series_list and all_dates:
            data = dict(data)  # don't mutate original
            data["dates"] = all_dates
            data["series"] = series_list
            if "chart_type" not in data:
                data["chart_type"] = "timeseries"
            if not data.get("source"):
                data["source"] = "Yahoo Finance"
            logger.info("Enriched chart with Yahoo Finance data: %d tickers, %d points",
                        len(series_list), len(all_dates))

    except ImportError:
        logger.warning("yfinance not installed — skipping Yahoo Finance enrichment")
    except Exception as exc:
        logger.warning("Yahoo Finance enrichment failed: %s", exc)

    return data


# ── Bar chart ──────────────────────────────────────────────────────────────

def _render_bar_chart(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    labels = data.get("labels", [])
    raw_values = [float(v) for v in data.get("values", [])]
    unit = data.get("unit", "")
    n = len(labels)
    if n == 0:
        return

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    lp = _label_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)

    # Staggered grow
    grow_dur = 0.45
    gap = (1.0 - grow_dur) / max(n, 1)
    values = []
    for i, v in enumerate(raw_values):
        t = max(0.0, min(1.0, (dp - i * gap) / grow_dur))
        t = 1.0 - (1.0 - t) ** 3
        values.append(v * t)

    x = np.arange(n)
    max_val = max(raw_values or [10])
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]

    ax.bar(x, values, color=colors, width=0.52, edgecolor="none", alpha=0.88, zorder=3)

    # Value labels
    for i, (raw, anim) in enumerate(zip(raw_values, values)):
        if anim > max_val * 0.01 and lp > 0:
            label = _format_value(anim) if unit == "$" else f"{anim:,.0f}"
            ax.text(x[i], anim + max_val * 0.02, label,
                    ha="center", va="bottom", color=TEXT_COLOR,
                    fontsize=11, fontweight="bold", alpha=lp)

    ax.set_ylim(0, max_val * 1.18)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30 if n > 5 else 0,
                       ha="right" if n > 5 else "center", fontsize=11)
    if unit == "$":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _format_value(v)))


# ── Line chart ─────────────────────────────────────────────────────────────

def _render_line_chart(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    labels = data.get("labels", [])
    series_list = data.get("series", [])
    if not series_list and "values" in data:
        series_list = [{"name": data.get("series_name", ""), "values": data["values"]}]

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    lp = _label_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)

    x = np.arange(len(labels))
    n = len(labels)
    if n < 2:
        return

    draw_pos = dp * (n - 1)

    for idx, series in enumerate(series_list):
        all_vals = [float(v) for v in series.get("values", [])]
        color = PALETTE[idx % len(PALETTE)]
        name = series.get("name", "")

        n_full = int(draw_pos)
        frac = draw_pos - n_full

        if n_full >= n - 1:
            xs, vals = list(x[:n]), list(all_vals[:n])
        elif n_full < 0:
            continue
        else:
            xs = list(x[:n_full + 1])
            vals = list(all_vals[:n_full + 1])
            if n_full + 1 < n and frac > 0:
                xs.append(x[n_full] + frac)
                vals.append(all_vals[n_full] + frac * (all_vals[n_full + 1] - all_vals[n_full]))

        if len(xs) > 0:
            ax.plot(xs, vals, color=color, linewidth=2.8, label=name,
                    zorder=3, solid_capstyle="round")
            ax.fill_between(xs, vals, alpha=0.04, color=color, zorder=1)

            # End-of-line value badge
            if lp > 0 and len(vals) > 0:
                end_val = vals[-1]
                unit = data.get("unit", "")
                badge_text = _format_pct(end_val) if data.get("value_type") == "pct_change" else (
                    _format_value(end_val) if unit == "$" else f"{end_val:,.0f}")
                ax.annotate(
                    badge_text,
                    xy=(xs[-1], end_val),
                    xytext=(12, 0), textcoords="offset points",
                    fontsize=11, fontweight="bold", color="white",
                    va="center", ha="left", alpha=lp,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=color,
                              edgecolor="none", alpha=0.9 * lp),
                    zorder=5,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30 if n > 6 else 0,
                       ha="right" if n > 6 else "center", fontsize=11)
    if len(series_list) > 1:
        leg = ax.legend(facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
                        fontsize=10, framealpha=0.95, loc="upper left")
        leg.get_frame().set_linewidth(0.5)
    all_values = [v for s in series_list for v in s.get("values", [])]
    if all_values:
        pad = (max(all_values) - min(all_values)) * 0.12 or 1
        ax.set_ylim(min(0, min(all_values)) - pad * 0.5, max(all_values) + pad)


# ── Horizontal bar chart ───────────────────────────────────────────────────

def _render_horizontal_bar(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    labels = data.get("labels", [])
    raw_values = [float(v) for v in data.get("values", [])]
    unit = data.get("unit", "")
    n = len(labels)
    if n == 0:
        return

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    lp = _label_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)

    grow_dur = 0.45
    gap = (1.0 - grow_dur) / max(n, 1)
    values = []
    for i, v in enumerate(raw_values):
        t = max(0.0, min(1.0, (dp - i * gap) / grow_dur))
        t = 1.0 - (1.0 - t) ** 3
        values.append(v * t)

    y_pos = np.arange(n)
    max_val = max(raw_values or [10])
    colors = [PALETTE[i % len(PALETTE)] for i in range(n)]

    ax.barh(y_pos, values, color=colors, height=0.52, edgecolor="none", alpha=0.88, zorder=3)

    for i, (raw, anim) in enumerate(zip(raw_values, values)):
        if anim > max_val * 0.01 and lp > 0:
            label = _format_value(anim) if unit == "$" else f"{anim:,.0f}"
            ax.text(anim + max_val * 0.015, y_pos[i], label,
                    ha="left", va="center", color=TEXT_COLOR,
                    fontsize=11, fontweight="bold", alpha=lp)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(0, max_val * 1.25)
    if unit == "$":
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _format_value(v)))


# ── Grouped bar chart ──────────────────────────────────────────────────────

def _render_grouped_bar(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    labels = data.get("labels", [])
    series_list = data.get("series", [])
    n_series = len(series_list)
    if n_series == 0:
        return

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)

    x = np.arange(len(labels))
    width = 0.7 / n_series

    for idx, series in enumerate(series_list):
        vals = [float(v) * dp for v in series.get("values", [])]
        offset = (idx - n_series / 2 + 0.5) * width
        color = PALETTE[idx % len(PALETTE)]
        ax.bar(x + offset, vals, width * 0.88, color=color, alpha=0.85,
               label=series.get("name", ""), zorder=3, edgecolor="none")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30 if len(labels) > 5 else 0,
                       ha="right" if len(labels) > 5 else "center", fontsize=11)
    leg = ax.legend(facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
                    fontsize=10, framealpha=0.95)
    leg.get_frame().set_linewidth(0.5)
    all_vals = [v for s in series_list for v in s.get("values", [])]
    ax.set_ylim(0, max(all_vals or [10]) * 1.25)


# ── Donut / Pie chart ──────────────────────────────────────────────────────

def _render_donut_chart(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    total = sum(values) or 1

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    lp = _label_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)
    ax.grid(False)

    sweep_p = min(1.0, dp / 0.85)
    sweep_p = 1.0 - (1.0 - sweep_p) ** 2
    sweep = sweep_p * 360.0

    show_vals, show_colors = [], []
    acc = 0.0
    for i, v in enumerate(values):
        angle = (v / total) * 360.0
        if acc >= sweep:
            break
        if acc + angle <= sweep:
            show_vals.append(v)
        else:
            show_vals.append(v * (sweep - acc) / angle)
        show_colors.append(colors[i])
        acc += angle

    if sum(show_vals) < total:
        show_vals.append(total - sum(show_vals))
        show_colors.append(BG_COLOR)

    wedge_props = {"edgecolor": "white", "linewidth": 2.5}
    is_donut = data.get("chart_subtype", "donut") == "donut"

    wedges, _, autotexts = ax.pie(
        show_vals, labels=None, colors=show_colors,
        autopct=lambda p: f"{p:.1f}%" if p > 3 and lp > 0.5 else "",
        pctdistance=0.75 if is_donut else 0.6,
        wedgeprops=wedge_props, startangle=90,
    )
    for t in autotexts:
        t.set_color(TEXT_COLOR)
        t.set_fontsize(11)
        t.set_fontweight("bold")
        t.set_alpha(lp)

    if is_donut:
        ax.add_artist(plt.Circle((0, 0), 0.55, fc="white"))
        center_value = data.get("center_value", "")
        center_label = data.get("center_label", "")
        if center_value and lp > 0:
            ax.text(0, 0.05, str(center_value), ha="center", va="center",
                    color=TEXT_COLOR, fontsize=24, fontweight="bold", alpha=lp)
        if center_label and lp > 0:
            ax.text(0, -0.18, center_label, ha="center", va="center",
                    color=MUTED_TEXT, fontsize=11, alpha=0.7 * lp)

    if lp > 0:
        legend = ax.legend(
            wedges[:len(labels)],
            [f"{l}  ({v:,.0f})" for l, v in zip(labels, values)],
            loc="center left", bbox_to_anchor=(1, 0.5),
            facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR, fontsize=10,
        )
        legend.get_frame().set_linewidth(0.5)
        for text in legend.get_texts():
            text.set_alpha(lp)


# ── Timeseries chart ───────────────────────────────────────────────────────

def _render_timeseries(data: dict, title: str, fig: plt.Figure, ax: plt.Axes, progress: float = 1.0) -> None:
    """Timeseries with smooth thick lines, end-of-line value badges, no markers."""
    from matplotlib.dates import DateFormatter, AutoDateLocator, date2num
    from datetime import datetime as dt

    dates_raw = data.get("dates", []) or data.get("labels", [])
    series_list = data.get("series", [])
    if not series_list and "values" in data:
        series_list = [{"name": data.get("series_name", ""), "values": data["values"]}]

    date_formats = ["%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y"]
    dates = []
    for d in dates_raw:
        parsed = None
        for fmt in date_formats:
            try:
                parsed = dt.strptime(str(d), fmt)
                break
            except ValueError:
                continue
        dates.append(parsed or dt(2020, 1, 1))

    n = len(dates)

    ap = _axis_progress(progress)
    dp = _data_progress(progress)
    lp = _label_progress(progress)
    _apply_theme(ax, fig, axis_alpha=ap)

    if n < 2:
        return

    # Set stable axis range
    all_values = [v for s in series_list for v in s.get("values", [])]
    if len(dates) >= 2:
        ax.set_xlim(dates[0], dates[-1])
    if all_values:
        vmin, vmax = min(all_values), max(all_values)
        pad = (vmax - vmin) * 0.12 or 1
        ax.set_ylim(min(0, vmin) - pad * 0.3, vmax + pad)

    draw_pos = dp * max(n - 1, 1)
    is_pct = data.get("value_type") == "pct_change"
    unit = data.get("unit", "")

    for idx, series in enumerate(series_list):
        all_vals = [float(v) for v in series.get("values", [])]
        color = PALETTE[idx % len(PALETTE)]
        name = series.get("name", "")

        n_full = int(draw_pos)
        frac = draw_pos - n_full
        n_vals = len(all_vals)

        if n_full >= n - 1 or n_full >= n_vals - 1:
            ds, vals = list(dates[:min(n, n_vals)]), list(all_vals[:min(n, n_vals)])
        elif n_full < 0:
            continue
        else:
            ds = list(dates[:n_full + 1])
            vals = list(all_vals[:n_full + 1])
            if n_full + 1 < n and n_full + 1 < n_vals and frac > 0:
                d0 = date2num(dates[n_full])
                d1 = date2num(dates[n_full + 1])
                ds.append(matplotlib.dates.num2date(d0 + frac * (d1 - d0)))
                vals.append(all_vals[n_full] + frac * (all_vals[n_full + 1] - all_vals[n_full]))

        if len(ds) > 0:
            # Thick smooth line, no markers
            ax.plot(ds, vals, color=color, linewidth=2.8, label=name,
                    zorder=3, solid_capstyle="round")
            ax.fill_between(ds, vals, alpha=0.03, color=color, zorder=1)

            # End-of-line value badge
            if lp > 0:
                end_val = vals[-1]
                if is_pct:
                    badge = _format_pct(end_val)
                elif unit == "$":
                    badge = _format_value(end_val)
                else:
                    badge = f"{end_val:,.0f}"
                ax.annotate(
                    badge,
                    xy=(ds[-1], end_val),
                    xytext=(10, 0), textcoords="offset points",
                    fontsize=11, fontweight="bold", color="white",
                    va="center", ha="left", alpha=lp,
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=color,
                              edgecolor="none", alpha=0.9 * lp),
                    zorder=5,
                )

    # Event markers
    events = data.get("events", [])
    for evt in events:
        evt_date = None
        for fmt in date_formats:
            try:
                evt_date = dt.strptime(str(evt.get("date", "")), fmt)
                break
            except ValueError:
                continue
        if evt_date and lp > 0:
            ax.axvline(x=evt_date, color="#ef4444", linewidth=1, linestyle="--",
                       alpha=0.4 * lp, zorder=4)
            ax.annotate(
                evt.get("label", ""),
                xy=(evt_date, ax.get_ylim()[1] * 0.92),
                fontsize=9, color="#ef4444", fontweight="bold",
                ha="center", va="top", alpha=lp,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#ef4444", alpha=0.85 * lp),
            )

    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%b\n'%y" if n > 12 else "%b '%y"))

    if len(series_list) > 1:
        leg = ax.legend(facecolor=BG_COLOR, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
                        fontsize=10, framealpha=0.95, loc="upper left",
                        ncol=min(len(series_list), 4))
        leg.get_frame().set_linewidth(0.5)

    if is_pct:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"+{v:.0f}%" if v >= 0 else f"{v:.0f}%"))
        # Zero line
        ax.axhline(y=0, color=AXIS_COLOR, linewidth=0.8, zorder=2)
    elif unit == "$":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: _format_value(v)))


# ── Chart type dispatcher ──────────────────────────────────────────────────

CHART_RENDERERS = {
    "bar": _render_bar_chart,
    "line": _render_line_chart,
    "area": _render_line_chart,
    "horizontal_bar": _render_horizontal_bar,
    "grouped_bar": _render_grouped_bar,
    "pie": _render_donut_chart,
    "donut": _render_donut_chart,
    "timeseries": _render_timeseries,
}


# ── Main render function ───────────────────────────────────────────────────

def render_data_chart(instruction: dict, output_dir: str = "output/charts",
                      duration: float = 8.0, fps: int = 30) -> str:
    """Render a data_chart instruction to an animated MP4.

    Animation phases:
      1. Title + axis construction (0.0–0.12)
      2. Data reveal (0.08–0.82)
      3. Value badges + labels (0.55–0.85)
      4. Hold final (0.85–1.0)

    If data contains `ticker`/`tickers` fields without pre-populated values,
    live price history is fetched from Yahoo Finance via yfinance.

    Returns:
        Absolute path to the rendered MP4.
    """
    data = instruction.get("data", {})
    title = instruction.get("title", "")
    subtitle = data.get("subtitle", "")
    source_label = data.get("source", "")

    # Enrich from Yahoo Finance if needed
    data = _enrich_from_yahoo(data)

    chart_type = data.get("chart_type", "bar")
    renderer_fn = CHART_RENDERERS.get(chart_type, _render_bar_chart)

    os.makedirs(output_dir, exist_ok=True)
    uid = uuid.uuid4().hex[:8]

    # Timeline
    intro_frames = int(fps * 0.15)
    anim_frames = int(fps * min(duration * 0.72, 5.5))
    hold_frames = max(0, int(fps * duration) - intro_frames - anim_frames)
    total_frames = intro_frames + anim_frames + hold_frames

    frame_dir = tempfile.mkdtemp(prefix="chart_frames_")

    for frame_idx in range(total_frames):
        if frame_idx < intro_frames:
            progress = 0.0
        elif frame_idx < intro_frames + anim_frames:
            t = (frame_idx - intro_frames) / anim_frames
            if t < 0.5:
                progress = 4.0 * t * t * t
            else:
                progress = 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0
        else:
            progress = 1.0

        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)

        # Renderer applies theme internally
        renderer_fn(data, title, fig, ax, progress=max(0.001, progress))

        # Title block (accent bar + title + subtitle + source)
        title_alpha = _axis_progress(progress)
        _draw_title_block(fig, title, subtitle, source_label, alpha=title_alpha)

        plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.85])
        frame_path = os.path.join(frame_dir, f"frame_{frame_idx:05d}.png")
        fig.savefig(frame_path, facecolor=fig.get_facecolor(), dpi=100,
                    bbox_inches="tight", pad_inches=0.3)
        plt.close(fig)

    # Stitch with FFmpeg — light bg padding
    output_path = os.path.join(output_dir, f"data_chart_{uid}.mp4")
    pad_hex = BG_COLOR.lstrip("#")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frame_dir, "frame_%05d.png"),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x{pad_hex}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        output_path,
    ]
    logger.info("Rendering data chart: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    import shutil
    shutil.rmtree(frame_dir, ignore_errors=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg chart render failed: {result.stderr[:500]}")

    logger.info("Data chart rendered: %s (%.1fs)", output_path, duration)
    return os.path.abspath(output_path)
