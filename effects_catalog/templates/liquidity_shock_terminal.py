"""Liquidity Shock (Terminal) — TradingView Lightweight Charts via Puppeteer.

Dark theme candlestick chart with volume bars, SMA 9/20, Bollinger Bands,
OHLC header, and shock event animation. Rendered using the actual TradingView
Lightweight Charts library through Puppeteer screenshot capture.

This is NOT a Manim template — it shells out to Node.js.
For the Manim line-chart version, see liquidity_shock_simple.py.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

SCENE_CLASS = "LiquidityShockTerminalScene"

# This template does NOT generate Manim code.
# It renders via Puppeteer and returns the path to the output video.
IS_EXTERNAL_RENDERER = True


def _compute_indicators(bars):
    """Compute SMA 9, SMA 20, Bollinger Bands from close prices."""
    closes = [b["close"] for b in bars]
    n = len(closes)

    def sma(period):
        result = []
        for i in range(n):
            if i < period - 1:
                result.append({"time": bars[i]["time"], "value": None})
            else:
                avg = sum(closes[i - period + 1:i + 1]) / period
                result.append({"time": bars[i]["time"], "value": round(avg, 2)})
        return result

    sma9 = sma(9)
    sma20 = sma(20)

    bb_upper, bb_lower = [], []
    for i in range(n):
        if sma20[i]["value"] is None:
            bb_upper.append({"time": bars[i]["time"], "value": None})
            bb_lower.append({"time": bars[i]["time"], "value": None})
        else:
            window = closes[i - 19:i + 1]
            mean = sma20[i]["value"]
            std = (sum((x - mean) ** 2 for x in window) / 20) ** 0.5
            bb_upper.append({"time": bars[i]["time"], "value": round(mean + 2 * std, 2)})
            bb_lower.append({"time": bars[i]["time"], "value": round(mean - 2 * std, 2)})

    return sma9, sma20, bb_upper, bb_lower


def _build_ohlc_from_closes(dates, values):
    """Generate synthetic OHLC + volume from close prices."""
    import random
    random.seed(42)
    bars = []
    for i, (date, close) in enumerate(zip(dates, values)):
        prev = values[i - 1] if i > 0 else close
        spread = abs(close) * 0.008
        op = prev + random.uniform(-0.3, 0.3) * spread
        body_top = max(op, close)
        body_bot = min(op, close)
        high = body_top + random.uniform(0.1, 0.5) * spread
        low = body_bot - random.uniform(0.1, 0.5) * spread
        move = abs(close - prev) / max(prev, 1) * 100
        vol = random.uniform(25, 55) * (1 + move * 1.5)
        bars.append({
            "time": date,
            "open": round(op, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(vol, 1),
        })
    return bars


def render(instruction: dict, output_path: str | None = None) -> str:
    """Render the terminal liquidity shock via Puppeteer + Lightweight Charts.

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
    exchange = data.get("exchange", "NasdaqGS")
    interval = data.get("interval_label", "1D")
    fps = int(data.get("fps", 30))

    # Resolve series → dates/values if needed
    if series and not values:
        s = series[0]
        pts = s.get("data", s.get("points", []))
        dates = [p.get("date", "") for p in pts]
        values = [p.get("value", p.get("close", 0)) for p in pts]

    if len(values) < 2:
        raise ValueError(f"Insufficient data: {len(values)} points")

    # Build OHLC bars
    bars = _build_ohlc_from_closes(dates, values)

    # Find shock index
    shock_idx = len(bars) // 2
    for i, b in enumerate(bars):
        if b["time"] == shock_date or b["time"].startswith(shock_date):
            shock_idx = i
            break

    # Compute indicators
    sma9, sma20, bb_upper, bb_lower = _compute_indicators(bars)

    # Build volumes
    volumes = []
    for b in bars:
        is_up = b["close"] >= b["open"]
        volumes.append({
            "time": b["time"],
            "value": b["volume"],
            "color": "rgba(38, 166, 154, 0.5)" if is_up else "rgba(239, 83, 80, 0.5)",
        })

    # Build config JSON for the Puppeteer recorder
    config = {
        "ohlc": bars,
        "volumes": volumes,
        "sma9": sma9,
        "sma20": sma20,
        "bbUpper": bb_upper,
        "bbLower": bb_lower,
        "ticker": ticker,
        "exchange": exchange,
        "interval": interval,
        "shockIdx": shock_idx,
        "shockLabel": shock_label,
        "shockSub": shock_sub,
        "animDelayMs": 80,
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
    import glob
    for frame in glob.glob(os.path.join(frames_dir, "frame_*.png")):
        os.unlink(frame)
    # Remove data file and dir
    try:
        os.unlink(data_path)
        os.rmdir(frames_dir)
    except OSError:
        pass

    logger.info("Rendered: %s", output_path)
    return output_path


def generate(instruction: dict) -> str:
    """For backward compatibility — returns a stub Manim scene that does nothing.

    The real rendering happens via render() which calls Puppeteer.
    Use render() directly for the terminal variant.
    """
    # Return minimal Manim stub so the effects catalog doesn't break
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
