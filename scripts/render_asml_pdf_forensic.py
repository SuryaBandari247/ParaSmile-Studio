#!/usr/bin/env python3
"""Render a PDF Forensic effect on the ASML Q3 2024 mock report.

Highlights the key lines that caused the crash:
  1. "2025 Outlook (REVISED DOWNWARD)" — the bombshell headline
  2. "€30-35 billion" — the revised revenue guidance
  3. "16% single-day stock decline" — the market reaction

Usage:
    python scripts/render_asml_pdf_forensic.py
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    print("=" * 60)
    print("ASML PDF Forensic — Cinematic Test Render")
    print("=" * 60)

    pdf_path = os.path.abspath("output/asml_q3_2024_mock.pdf")
    if not os.path.exists(pdf_path):
        print(f"✗ PDF not found: {pdf_path}")
        print("  Run the mock PDF generator first.")
        return

    print(f"\nPDF: {pdf_path}")

    # Build instruction with highlight bboxes + zoom_level per highlight
    # bbox coordinates are relative (0-1) on the page
    # zoom_level controls how tight the camera zooms (lower = tighter)
    instruction = {
        "type": "pdf_forensic",
        "title": "ASML Q3 2024 — The Earnings Leak",
        "data": {
            "pdf_path": pdf_path,
            "page_number": 1,
            "camera_shake": True,
            "desk_texture": "dark",
            "highlights": [
                {
                    "bbox": {"x": 0.10, "y": 0.36, "width": 0.55, "height": 0.025},
                    "style": "rectangle",
                    "color": "#EF4444",
                    "opacity": 0.25,
                    "label": "REVISED DOWNWARD — the bombshell",
                    "zoom_level": 3.5,
                },
                {
                    "bbox": {"x": 0.10, "y": 0.39, "width": 0.65, "height": 0.025},
                    "style": "rectangle",
                    "color": "#FF9800",
                    "opacity": 0.2,
                    "label": "Revenue guidance: €30-35B (was €40-44B)",
                    "zoom_level": 4.0,
                },
                {
                    "bbox": {"x": 0.10, "y": 0.47, "width": 0.70, "height": 0.025},
                    "style": "underline",
                    "color": "#EF4444",
                    "opacity": 0.3,
                    "label": "16% single-day decline — market reaction",
                    "zoom_level": 5.0,
                },
            ],
        },
    }

    print("\n[1/2] Generating Manim code...")
    from effects_catalog.templates.pdf_forensic import generate
    manim_code = generate(instruction)

    output_dir = os.path.abspath("output/renders")
    os.makedirs(output_dir, exist_ok=True)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".py", prefix="asml_pdf_forensic_",
        delete=False, mode="w", dir=output_dir,
    )
    tmp.write(manim_code)
    tmp.flush()
    tmp.close()
    print(f"  ✓ {len(manim_code)} chars → {tmp.name}")

    print("\n[2/2] Rendering with Manim...")
    output_filename = "asml_pdf_forensic.mp4"
    cmd = [
        "manim", "render",
        "-qm", "--fps", "30",
        "-o", output_filename,
        "--media_dir", output_dir,
        tmp.name,
        "PDFForensicScene",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  ✗ Manim failed:")
            print(f"    {result.stderr[-800:]}")
            print(f"  Temp file: {tmp.name}")
            return
        print("  ✓ Render complete")
    except subprocess.TimeoutExpired:
        print("  ✗ Timed out (180s)")
        return

    # Find output
    rendered = None
    for dirpath, _, filenames in os.walk(output_dir):
        if output_filename in filenames:
            rendered = os.path.join(dirpath, output_filename)
            break

    if rendered:
        size_mb = os.path.getsize(rendered) / (1024 * 1024)
        print(f"\n{'=' * 60}")
        print(f"✅ Rendered: {rendered}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"{'=' * 60}")

        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", rendered],
            capture_output=True, text=True,
        )
        if probe.returncode == 0:
            streams = json.loads(probe.stdout)
            for s in streams.get("streams", []):
                if s.get("codec_type") == "video":
                    print(f"   Video: {s['width']}x{s['height']} @ {s['r_frame_rate']} fps, {s.get('duration','?')}s")
    else:
        print(f"\n✗ Could not find {output_filename}")

    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


if __name__ == "__main__":
    main()
