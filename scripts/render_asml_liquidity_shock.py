#!/usr/bin/env python3
"""Render a single Liquidity Shock effect for ASML Scene 11 (Oct 2024 Flash Crash).

Usage:
    source venv/bin/activate
    python scripts/render_asml_liquidity_shock.py
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def _generate_asml_fallback_data():
    """Generate realistic ASML price data when Yahoo Finance is unavailable.

    Based on actual ASML price history around the Oct 2024 crash:
    - Jul 2024: ~€950-1000 (peak before crash)
    - Oct 15 2024: ~€630 (crash day, -16%)
    - Dec 2024: ~€680-700 (partial recovery)
    """
    import random
    random.seed(42)  # Reproducible

    base_date = datetime(2024, 7, 1)
    dates = []
    values = []

    # Phase 1: Jul-Sep 2024 — gradual climb to peak (~75 trading days)
    price = 880.0
    for i in range(75):
        d = base_date + timedelta(days=i * 7 // 5)  # skip weekends roughly
        if d.weekday() >= 5:
            continue
        dates.append(d.strftime("%Y-%m-%d"))
        values.append(round(price, 2))
        price += random.uniform(-8, 12)  # slight upward drift
        price = max(price, 820)

    # Phase 2: Early Oct — slight decline before crash (~10 days)
    for i in range(10):
        d = datetime(2024, 10, 1) + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        dates.append(d.strftime("%Y-%m-%d"))
        price -= random.uniform(2, 15)
        values.append(round(price, 2))

    # Phase 3: Oct 15 — THE CRASH (-16% in one day)
    pre_crash = price
    dates.append("2024-10-15")
    price = pre_crash * 0.84  # -16%
    values.append(round(price, 2))

    # Phase 4: Oct 16-31 — volatile aftermath
    for i in range(1, 12):
        d = datetime(2024, 10, 16) + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        dates.append(d.strftime("%Y-%m-%d"))
        price += random.uniform(-20, 25)
        values.append(round(price, 2))

    # Phase 5: Nov-Dec 2024 — slow recovery (~40 trading days)
    for i in range(40):
        d = datetime(2024, 11, 1) + timedelta(days=i * 7 // 5)
        if d.weekday() >= 5:
            continue
        dates.append(d.strftime("%Y-%m-%d"))
        price += random.uniform(-5, 10)
        values.append(round(price, 2))

    return dates, values


def main():
    print("=" * 60)
    print("ASML Liquidity Shock — Test Render")
    print("=" * 60)

    # Load Scene 11 from the ASML script
    with open("output/asml_new_video_script.json") as f:
        script = json.load(f)

    scene_11 = next(s for s in script["scenes"] if s["scene_number"] == 11)
    vi = scene_11["visual_instruction"]
    print(f"\nScene 11: {vi['title']}")
    print(f"Narration: {scene_11['narration_text'][:80]}...")

    # Step 1: Try Yahoo Finance, fall back to synthetic data
    print("\n[1/3] Fetching ASML price data...")
    dates = []
    values = []

    try:
        from asset_orchestrator.manim_codegen import _enrich_from_yahoo
        enriched_data = _enrich_from_yahoo(vi["data"])
        series = enriched_data.get("series", [])
        dates = enriched_data.get("dates", [])
        values = series[0]["values"] if series else []
    except Exception as e:
        print(f"  ⚠ Yahoo Finance failed: {e}")

    if not values or len(values) < 10:
        print("  ⚠ Yahoo Finance unavailable, using realistic fallback data...")
        dates, values = _generate_asml_fallback_data()
        print(f"  ✓ Generated {len(values)} synthetic data points (Jul-Dec 2024)")
    else:
        print(f"  ✓ {len(values)} live data points from Yahoo Finance")

    # Step 2: Build liquidity_shock instruction
    print("\n[2/3] Generating Manim code via liquidity_shock template...")

    shock_date = "2024-10-15"
    shock_label = "Earnings Leak — 16% Crash"
    subtitle = vi["data"].get("subtitle", "16% single-day crash — €50B erased in hours")
    source = vi["data"].get("source", "Yahoo Finance")

    liquidity_instruction = {
        "type": "liquidity_shock",
        "title": vi["title"],
        "data": {
            "dates": dates,
            "values": values,
            "shock_date": shock_date,
            "shock_label": shock_label,
            "shock_color": "#FF453A",
            "shock_intensity": 0.8,
            "subtitle": subtitle,
            "source": source,
            "unit": "$",
        },
    }

    from effects_catalog.templates.liquidity_shock import generate
    manim_code = generate(liquidity_instruction)

    # Write to temp file
    output_dir = os.path.abspath("output/renders")
    os.makedirs(output_dir, exist_ok=True)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".py", prefix="asml_liquidity_shock_",
        delete=False, mode="w", dir=output_dir,
    )
    tmp.write(manim_code)
    tmp.flush()
    tmp.close()
    print(f"  ✓ Generated {len(manim_code)} chars of Manim code")
    print(f"  ✓ Temp file: {tmp.name}")

    # Step 3: Render with Manim
    print("\n[3/3] Rendering with Manim (medium quality)...")
    output_filename = "asml_liquidity_shock_v13.mp4"

    cmd = [
        "manim", "render",
        "-qm",           # medium quality (720p) for speed
        "--fps", "30",
        "-o", output_filename,
        "--media_dir", output_dir,
        tmp.name,
        "LiquidityShockScene",
    ]

    print(f"  Running: manim render -qm --fps 30 ...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            print(f"  ✗ Manim render failed:")
            print(f"    stderr: {result.stderr[-800:]}")
            print(f"  ℹ Temp file kept for debugging: {tmp.name}")
            return

        print(f"  ✓ Manim render complete")
    except subprocess.TimeoutExpired:
        print("  ✗ Manim render timed out (180s)")
        return

    # Find the rendered file
    rendered_path = None
    for dirpath, _, filenames in os.walk(output_dir):
        if output_filename in filenames:
            rendered_path = os.path.join(dirpath, output_filename)
            break

    if rendered_path:
        size_mb = os.path.getsize(rendered_path) / (1024 * 1024)
        print(f"\n{'=' * 60}")
        print(f"✅ Rendered: {rendered_path}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"{'=' * 60}")

        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_streams", rendered_path],
                capture_output=True, text=True,
            )
            if probe.returncode == 0:
                streams = json.loads(probe.stdout)
                for stream in streams.get("streams", []):
                    if stream.get("codec_type") == "video":
                        w = stream.get("width")
                        h = stream.get("height")
                        fps = stream.get("r_frame_rate", "?")
                        dur = stream.get("duration", "?")
                        print(f"   Video: {w}x{h} @ {fps} fps, duration={dur}s")
        except Exception:
            pass
    else:
        print(f"\n✗ Could not find {output_filename} in {output_dir}")
        for dirpath, _, files in os.walk(output_dir):
            for f in files[-5:]:
                print(f"  Found: {os.path.join(dirpath, f)}")

    # Clean up temp file
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)
        print(f"  ✓ Cleaned up temp file")


if __name__ == "__main__":
    main()
