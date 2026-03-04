#!/usr/bin/env python3
"""Render visuals only for the Moronic Monday script — no audio."""

import json
import os
import subprocess
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from asset_orchestrator.orchestrator import AssetOrchestrator


def main():
    script_path = "output/moronic_monday_video_script.json"
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
        print(f"▶ Scene {sn}: {vi['type']} — {vi.get('title', '')}")

        try:
            result = orchestrator.process_instruction(
                vi, audio_path=None, narration_text=narration
            )
            results.append(result)
            if result["status"] == "success":
                print(f"  ✅ {result['output_path']}")
            else:
                print(f"  ❌ {result.get('error', 'unknown')}")
        except Exception as e:
            print(f"  ❌ {e}")
            results.append({"status": "error", "error": str(e)})

    ok_paths = [r["output_path"] for r in results if r.get("status") == "success"]
    failed = len(results) - len(ok_paths)
    print(f"\n{'='*50}")
    print(f"Rendered: {len(ok_paths)}/{len(scenes)} scenes ({failed} failed)")

    if len(ok_paths) > 1:
        os.makedirs("output/final", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final = f"output/final/moronic_monday_{ts}.mp4"
        concat_file = "output/concat_list.txt"

        with open(concat_file, "w") as f:
            for p in ok_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
               "-i", concat_file, "-c", "copy", final]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"\n✅ Final video: {os.path.abspath(final)}")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Concat failed: {e.stderr[:300]}")
    elif ok_paths:
        print(f"\n✅ Single scene: {os.path.abspath(ok_paths[0])}")
    else:
        print("\n❌ No scenes rendered.")


if __name__ == "__main__":
    main()
