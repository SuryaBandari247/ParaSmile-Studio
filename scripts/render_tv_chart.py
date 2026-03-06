#!/usr/bin/env python3
"""Render ASML Liquidity Shock as a TradingView Lightweight Charts animation.

Uses Puppeteer to record the chart building candle-by-candle, then FFmpeg
to stitch frames into video.

Usage:
    python scripts/render_tv_chart.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()


def _next_weekday(d):
    """Advance date to next weekday if it falls on weekend."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _generate_asml_ohlc():
    """Generate realistic ASML OHLC + volume data around Oct 2024 crash.

    CRITICAL: All dates must be strictly ascending and unique — Lightweight
    Charts silently drops data with duplicate or out-of-order timestamps.
    """
    import random
    random.seed(42)

    bars = []
    price = 880.0

    def _add_bar(date, close, prev_close):
        spread = abs(close) * 0.008
        op = prev_close + random.uniform(-0.3, 0.3) * spread
        body_top = max(op, close)
        body_bot = min(op, close)
        high = body_top + random.uniform(0.1, 0.5) * spread
        low = body_bot - random.uniform(0.1, 0.5) * spread
        move = abs(close - prev_close) / max(prev_close, 1) * 100
        vol = random.uniform(25, 55) * (1 + move * 1.5)
        bars.append({
            "time": date.strftime("%Y-%m-%d"),
            "open": round(op, 2), "high": round(high, 2),
            "low": round(low, 2), "close": round(close, 2),
            "volume": round(vol, 1),
        })

    # Phase 1: Jul 1 — Sep 30 — gradual climb to ~1050
    d = datetime(2024, 7, 1)
    for i in range(65):
        d = _next_weekday(d)
        prev = price
        price += random.uniform(-6, 10)
        price = max(price, 840)
        _add_bar(d, price, prev)
        d += timedelta(days=1)

    # Phase 2: Oct 1 — Oct 14 — slight decline (10 trading days)
    d = datetime(2024, 10, 1)
    for i in range(10):
        d = _next_weekday(d)
        prev = price
        price -= random.uniform(2, 12)
        _add_bar(d, price, prev)
        d += timedelta(days=1)

    # Phase 3: Oct 15 — THE CRASH (single bar, -16%)
    d = _next_weekday(d)
    prev = price
    price = prev * 0.84
    _add_bar(d, price, prev)
    crash_date = d.strftime("%Y-%m-%d")
    d += timedelta(days=1)

    # Phase 4: Oct 16-31 — volatile aftermath
    for i in range(10):
        d = _next_weekday(d)
        prev = price
        price += random.uniform(-15, 20)
        _add_bar(d, price, prev)
        d += timedelta(days=1)

    # Phase 5: Nov-Dec — slow recovery
    for i in range(40):
        d = _next_weekday(d)
        prev = price
        price += random.uniform(-4, 9)
        _add_bar(d, price, prev)
        d += timedelta(days=1)

    # Verify uniqueness
    dates = [b["time"] for b in bars]
    assert len(dates) == len(set(dates)), f"Duplicate dates found: {len(dates)} vs {len(set(dates))} unique"
    # Verify ascending order
    for i in range(1, len(dates)):
        assert dates[i] > dates[i-1], f"Out of order: {dates[i-1]} >= {dates[i]} at index {i}"

    return bars, crash_date


def _compute_indicators(bars):
    """Compute SMA 9, SMA 20, Bollinger Bands from OHLC bars."""
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

    bb_upper = []
    bb_lower = []
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


def main():
    print("=" * 60)
    print("ASML Liquidity Shock — TradingView Chart Render")
    print("=" * 60)

    # Generate data
    print("\n[1/4] Generating OHLC data...")
    bars, crash_date = _generate_asml_ohlc()
    print(f"  ✓ {len(bars)} bars generated (unique ascending dates verified)")

    # Find shock index
    shock_idx = next(
        (i for i, b in enumerate(bars) if b["time"] == crash_date),
        len(bars) // 2,
    )
    print(f"  ✓ Shock at index {shock_idx} ({bars[shock_idx]['time']})")

    # Compute indicators
    print("\n[2/4] Computing indicators...")
    sma9, sma20, bb_upper, bb_lower = _compute_indicators(bars)
    print("  ✓ SMA 9, SMA 20, BB 20,2")

    # Build volumes array for Lightweight Charts format
    volumes = []
    for b in bars:
        is_up = b["close"] >= b["open"]
        volumes.append({
            "time": b["time"],
            "value": b["volume"],
            "color": "rgba(38, 166, 154, 0.5)" if is_up else "rgba(239, 83, 80, 0.5)",
        })

    # Build config JSON
    config = {
        "ohlc": bars,
        "volumes": volumes,
        "sma9": sma9,
        "sma20": sma20,
        "bbUpper": bb_upper,
        "bbLower": bb_lower,
        "ticker": "ASML",
        "exchange": "NasdaqGS",
        "interval": "1D",
        "shockIdx": shock_idx,
        "shockLabel": "Earnings Leak",
        "shockSub": "-16% Single Day",
        "animDelayMs": 80,
    }

    output_dir = os.path.abspath("output/chart_frames")
    os.makedirs(output_dir, exist_ok=True)

    data_path = os.path.join(output_dir, "chart_data.json")
    with open(data_path, "w") as f:
        json.dump(config, f)
    print(f"\n[3/4] Recording chart animation via Puppeteer...")
    print(f"  Data: {data_path}")

    # Run Node.js recorder
    recorder = os.path.join(os.path.dirname(__file__), "..", "chart_renderer", "record_chart.js")
    cmd = ["node", os.path.abspath(recorder), data_path, output_dir, "30"]
    print(f"  Running: node record_chart.js ...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ✗ Recorder failed:\n{result.stderr[-1000:]}")
        return

    # Stitch frames with FFmpeg
    print("\n[4/4] Stitching frames with FFmpeg...")
    output_video = os.path.abspath("output/renders/asml_tv_chart_v2.mp4")
    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", "30",
        "-i", os.path.join(output_dir, "frame_%06d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        output_video,
    ]
    ff_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
    if ff_result.returncode != 0:
        print(f"  ✗ FFmpeg failed:\n{ff_result.stderr[-500:]}")
        return

    size_mb = os.path.getsize(output_video) / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"✅ Rendered: {output_video}")
    print(f"   Size: {size_mb:.2f} MB")
    print(f"{'=' * 60}")

    # Probe
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", output_video],
            capture_output=True, text=True,
        )
        if probe.returncode == 0:
            streams = json.loads(probe.stdout)
            for s in streams.get("streams", []):
                if s.get("codec_type") == "video":
                    print(f"   Video: {s.get('width')}x{s.get('height')} @ {s.get('r_frame_rate')} fps")
    except Exception:
        pass

    # Cleanup frames
    import glob
    frames = glob.glob(os.path.join(output_dir, "frame_*.png"))
    for f in frames:
        os.unlink(f)
    print(f"  ✓ Cleaned up {len(frames)} frames")


if __name__ == "__main__":
    main()
