#!/usr/bin/env python3
"""Render visuals only (no audio) — for testing Manim scene output."""

import json
import os
import subprocess
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from asset_orchestrator.orchestrator import AssetOrchestrator


def main():
    script_path = "output/video_script.json"
    if not os.path.isfile(script_path):
        print("❌ No video_script.json found in output/. Run the pipeline first.")
        sys.exit(1)

    with open(script_path) as f:
        data = json.load(f)

    scenes = sorted(data["scenes"], key=lambda s: s["scene_number"])
    print(f"Title: {data['title']}")
    print(f"Scenes: {len(scenes)}\n")

    orchestrator = AssetOrchestrator()
    results = []

    for scene in scenes:
        sn = scene["scene_number"]
        vi = scene["visual_instruction"]
        narration = scene.get("narration_text", "")
        print(f"▶ Rendering scene {sn} ({vi['type']}: {vi.get('title', '')})...")

        try:
            result = orchestrator.process_instruction(
                vi, audio_path=None, narration_text=narration
            )
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ {result['output_path']}")
            else:
                print(f"  ❌ {result.get('error', 'unknown error')}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({"status": "error", "error": str(e)})

    # Concatenate successful scenes
    ok_paths = [r["output_path"] for r in results if r.get("status") == "success"]
    print(f"\n{'='*50}")
    print(f"Rendered: {len(ok_paths)}/{len(scenes)} scenes")

    if len(ok_paths) > 1:
        os.makedirs("output/final", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final = f"output/final/visuals_only_{ts}.mp4"
        concat_file = "output/concat_list.txt"

        with open(concat_file, "w") as f:
            for p in ok_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
               "-i", concat_file, "-c", "copy", final]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Final video: {os.path.abspath(final)}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Concat failed: {e.stderr[:200]}")
    elif ok_paths:
        print(f"✅ Single scene: {os.path.abspath(ok_paths[0])}")
    else:
        print("❌ No scenes rendered successfully.")


if __name__ == "__main__":
    main()
