#!/usr/bin/env python3
"""
Trial run — end-to-end test of the Asset Orchestrator pipeline.

Validates a Visual_Instruction through the pipeline, then renders
a real Manim bar chart to MP4 using FFmpeg.

Usage:
    source venv/bin/activate
    python examples/trial_run.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asset_orchestrator.scene_mapper import SceneMapper
from asset_orchestrator.scene_registry import SceneRegistry
from asset_orchestrator.chart_templates import _truncate_title, _group_categories, BACKGROUND_COLOR, TEXT_COLOR, ACCENT_COLORS
from asset_orchestrator.renderer import Renderer
from asset_orchestrator.config import RenderConfig


def main():
    print("=" * 60)
    print("Asset Orchestrator — Trial Run")
    print("=" * 60)

    # -- Step 1: Pipeline validation -----------------------------------------
    print("\n[1/4] Validating instruction through pipeline...")

    registry = SceneRegistry()
    mapper = SceneMapper(registry)

    instruction = {
        "type": "bar_chart",
        "title": "AWS Outage Impact by Region",
        "data": {
            "labels": ["us-east-1", "eu-west-1", "ap-southeast-1", "us-west-2", "eu-central-1"],
            "values": [47, 23, 12, 31, 18],
        },
    }

    scene = mapper.map(instruction)
    scene.construct()

    print(f"  ✓ Instruction validated: type={instruction['type']}")
    print(f"  ✓ Scene mapped: {scene.__class__.__name__}")
    print(f"  ✓ Title: {scene.processed_title}")
    print(f"  ✓ Background: {scene.background_color}")
    print(f"  ✓ Bars: {len(scene.bars)} regions")
    for bar in scene.bars:
        print(f"    - {bar['label']}: {bar['value']}% ({bar['color']})")

    # -- Step 2: Render with real Manim --------------------------------------
    print("\n[2/4] Rendering bar chart with Manim...")

    # Write a temporary Manim scene file
    import tempfile
    import subprocess

    output_dir = os.path.abspath("output/renders")
    os.makedirs(output_dir, exist_ok=True)

    # Build a real Manim scene script using only Pango-based primitives (no LaTeX)
    bars_data = [
        {"label": bar["label"], "value": bar["value"], "color": bar["color"]}
        for bar in scene.bars
    ]
    max_value = max(bar["value"] for bar in scene.bars)

    manim_script = '''
from manim import *

class AWSOutageBarChart(Scene):
    def construct(self):
        # Dark background
        self.camera.background_color = "{bg_color}"

        # Title (Pango-based Text, no LaTeX)
        title = Text("{title}", font_size=36, color="{text_color}")
        title.to_edge(UP, buff=0.5)
        self.play(Write(title))

        # Bar chart data
        bars_data = {bars_data}
        max_value = {max_value}
        num_bars = len(bars_data)

        # Layout constants
        chart_width = 10.0
        chart_height = 4.0
        bar_spacing = chart_width / num_bars
        bar_width = bar_spacing * 0.6

        # Build bars, x-labels, and value labels
        bar_group = VGroup()
        label_group = VGroup()
        value_group = VGroup()

        start_x = -(chart_width / 2) + (bar_spacing / 2)

        for i, entry in enumerate(bars_data):
            # Bar height proportional to value
            bar_height = (entry["value"] / max_value) * chart_height if max_value > 0 else 0.1
            bar = Rectangle(
                width=bar_width,
                height=bar_height,
                fill_color=entry["color"],
                fill_opacity=0.85,
                stroke_color=entry["color"],
                stroke_width=1,
            )
            x_pos = start_x + i * bar_spacing
            # Align bar bottom to a baseline
            bar.move_to([x_pos, -1.5 + bar_height / 2, 0])
            bar_group.add(bar)

            # X-axis label (Pango Text)
            x_label = Text(entry["label"], font_size=18, color="{text_color}")
            x_label.next_to(bar, DOWN, buff=0.15)
            label_group.add(x_label)

            # Value label above bar (Pango Text)
            val_label = Text(str(entry["value"]) + "%", font_size=20, color="{text_color}")
            val_label.next_to(bar, UP, buff=0.1)
            value_group.add(val_label)

        # Draw a baseline axis
        axis_line = Line(
            start=[-(chart_width / 2), -1.5, 0],
            end=[(chart_width / 2), -1.5, 0],
            color="{text_color}",
            stroke_width=2,
        )

        # Animate
        self.play(Create(axis_line), run_time=0.5)
        self.play(
            *[Create(bar) for bar in bar_group],
            *[FadeIn(lbl) for lbl in label_group],
            run_time=2,
        )
        self.play(*[FadeIn(vl) for vl in value_group], run_time=0.8)
        self.wait(2)
'''.format(
        bg_color=scene.background_color,
        text_color=scene.text_color,
        title=scene.processed_title,
        bars_data=bars_data,
        max_value=max_value,
    )

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".py", prefix="manim_trial_", delete=False, mode="w")
    tmp.write(manim_script)
    tmp.flush()
    tmp.close()

    output_filename = "bar_chart_AWS_Outage_Impact_by_Region.mp4"

    cmd = [
        "manim", "render",
        "-qm",  # medium quality for speed
        "--fps", "30",
        "-o", output_filename,
        "--media_dir", output_dir,
        tmp.name,
        "AWSOutageBarChart",
    ]

    print(f"  Running: {' '.join(cmd[:6])}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"  ✗ Manim render failed:")
            print(f"    stderr: {result.stderr[-500:]}")
            os.unlink(tmp.name)
            return
        
        print(f"  ✓ Manim render complete")

    except subprocess.TimeoutExpired:
        print("  ✗ Manim render timed out (120s)")
        os.unlink(tmp.name)
        return
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    # -- Step 3: Find the rendered file --------------------------------------
    print("\n[3/4] Locating rendered MP4...")

    rendered_path = None
    for dirpath, _, filenames in os.walk(output_dir):
        if output_filename in filenames:
            rendered_path = os.path.join(dirpath, output_filename)
            break

    if rendered_path:
        size_mb = os.path.getsize(rendered_path) / (1024 * 1024)
        print(f"  ✓ Found: {rendered_path}")
        print(f"  ✓ Size: {size_mb:.2f} MB")
    else:
        print(f"  ✗ Could not find {output_filename} in {output_dir}")
        # List what's there
        for dirpath, dirs, files in os.walk(output_dir):
            for f in files:
                print(f"    Found: {os.path.join(dirpath, f)}")
        return

    # -- Step 4: Verify with ffprobe -----------------------------------------
    print("\n[4/4] Verifying output with ffprobe...")

    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", rendered_path],
            capture_output=True, text=True
        )
        if probe.returncode == 0:
            import json
            streams = json.loads(probe.stdout)
            for stream in streams.get("streams", []):
                if stream.get("codec_type") == "video":
                    w = stream.get("width")
                    h = stream.get("height")
                    fps = stream.get("r_frame_rate", "?")
                    codec = stream.get("codec_name", "?")
                    print(f"  ✓ Video: {w}x{h} @ {fps} fps, codec={codec}")
        else:
            print("  ⚠ ffprobe not available, skipping verification")
    except FileNotFoundError:
        print("  ⚠ ffprobe not found, skipping verification")

    # -- Done ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Trial run complete!")
    print(f"Output: {rendered_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
