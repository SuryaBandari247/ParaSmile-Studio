"""Liquidity Shock (Terminal) — Cinematic narrative chart via Puppeteer.

Clean area-line chart on dark editorial background with smooth zoom,
shock annotation, and title overlay. No trading indicators — storytelling only.

Rendered using TradingView Lightweight Charts through Puppeteer.
This is NOT a Manim template — it shells out to Node.js.
For the Manim line-chart version, see liquidity_shock_simple.py.
"""

from __future__ import annotations

import glob
import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

SCENE_CLASS = "LiquidityShockTerminalScene"
IS_EXTERNAL_RENDERER = True


def _build_ohlc_from_closes(dates, values):
    """Generate synthetic OHLC from close prices.

    The recorder only uses the close for the area series, but we keep
    OHLC structure so the data format stays consistent if we ever
    want to switch back to candlesticks for a different template.
    """
    import random
    random.seed(42)
    bars = []
    for i, (date, close) in enumerate(zip(dates, values)):
        prev = values[i - 1] if i > 0 else close
        spread = abs(close) * 0.008
        op = prev + random.uniform(-0.3, 0.3) * spread
        high = max(op, close) + random.uniform(0.1, 0.5) * spread
        low = min(op, close) - random.uniform(0.1, 0.5) * spread
        bars.append({
            "time": date,
            "open": round(op, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
        })
    return bars


def render(instruction: dict, output_path: str | None = None) -> str:
    """Render the narrative liquidity shock via Puppeteer + Lightweight Charts.

    Returns the path to the rendered .mp4 file.
    """
    data = instruction.get("data", {})
    dates = data.get("dates", [])
    values = data.get("values", [])
    series = data.get("series", [])
    shock_date = data.get("shock_date", "")
    shock_label = data.get("shock_label", "")
    shock_sub = data.get("shock_caption", data.get("subtitle", ""))
    ticker = data.get("ticker", "ASML")
    source = data.get("source", "")
    fps = int(data.get("fps", 30))

    # Editorial metadata
    title = instruction.get("title", f"{ticker}")
    subtitle = data.get("subtitle", "")

    # Resolve series → dates/values if needed
    if series and not values:
        s = series[0]
        pts = s.get("data", s.get("points", []))
        dates = [p.get("date", "") for p in pts]
        values = [p.get("value", p.get("close", 0)) for p in pts]

    if len(values) < 2:
        raise ValueError(f"Insufficient data: {len(values)} points")

    # Build OHLC bars (recorder uses .close for area series)
    bars = _build_ohlc_from_closes(dates, values)

    # Find shock index
    shock_idx = len(bars) // 2
    for i, b in enumerate(bars):
        if b["time"] == shock_date or b["time"].startswith(shock_date):
            shock_idx = i
            break

    # Clean config — no indicators, no volume
    config = {
        "ohlc": bars,
        "title": title,
        "subtitle": subtitle,
        "source": source,
        "ticker": ticker,
        "shockIdx": shock_idx,
        "shockLabel": shock_label,
        "shockSub": shock_sub,
    }

    # Write config to temp file
    frames_dir = tempfile.mkdtemp(prefix="tv_frames_")
    data_path = os.path.join(frames_dir, "chart_data.json")
    with open(data_path, "w") as f:
        json.dump(config, f)

    logger.info("Rendering %d bars via Puppeteer (%s)", len(bars), ticker)

    # Run the Puppeteer recorder
    recorder = os.path.join(
        os.path.dirname(__file__), "..", "..", "chart_renderer", "record_chart.js"
    )
    recorder = os.path.abspath(recorder)

    cmd = ["node", recorder, data_path, frames_dir, str(fps)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Puppeteer recorder failed:\n{result.stderr[-500:]}")

    logger.info("Puppeteer: %s", result.stdout.strip().split("\n")[-1])

    # Stitch frames with FFmpeg
    if output_path is None:
        output_path = os.path.join(frames_dir, "..", "liquidity_shock_terminal.mp4")
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        output_path,
    ]
    ff = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
    if ff.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{ff.stderr[-500:]}")

    # Cleanup frames
    for frame in glob.glob(os.path.join(frames_dir, "frame_*.png")):
        os.unlink(frame)
    try:
        os.unlink(data_path)
        os.rmdir(frames_dir)
    except OSError:
        pass

    logger.info("Rendered: %s", output_path)
    return output_path


def generate(instruction: dict) -> str:
    """Backward compat stub — use render() directly."""
    return f'''from manim import *

class {SCENE_CLASS}(Scene):
    """Stub — terminal variant renders via Puppeteer, not Manim.
    Call liquidity_shock_terminal.render() instead.
    """
    def construct(self):
        t = Text("Terminal variant uses Puppeteer renderer", font_size=24)
        self.add(t)
        self.wait(2)
'''
