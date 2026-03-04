#!/usr/bin/env python3
"""Render all scenes from a video script JSON directly via AssetOrchestrator.

Usage:
    python render_test_script.py                          # uses output/test_video_script.json
    python render_test_script.py path/to/script.json      # custom script
"""

from __future__ import annotations

import json
import logging
import sys
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("render_script")


def main() -> None:
    script_path = sys.argv[1] if len(sys.argv) > 1 else "output/test_video_script.json"

    if not os.path.isfile(script_path):
        logger.error("Script not found: %s", script_path)
        sys.exit(1)

    with open(script_path) as f:
        script = json.load(f)

    title = script.get("title", "Untitled")
    scenes = script.get("scenes", [])
    logger.info("Loaded '%s' — %d scenes", title, len(scenes))

    from asset_orchestrator.orchestrator import AssetOrchestrator

    orch = AssetOrchestrator(log_level="INFO")

    instructions = []
    narration_texts = []

    for scene in scenes:
        vi = scene.get("visual_instruction", {})
        instruction = {
            "type": vi.get("type", "stock_with_text"),
            "title": vi.get("title", f"Scene {scene.get('scene_number', '?')}"),
            "data": vi.get("data", {}),
            "scene_number": scene.get("scene_number", 0),
        }
        instructions.append(instruction)
        narration_texts.append(scene.get("narration_text", ""))

    result = orch.process_batch(instructions, narration_texts=narration_texts)

    logger.info("Done — %d/%d succeeded, %d failed", result.succeeded, result.total, result.failed)
    for i, r in enumerate(result.results):
        status = r["status"]
        if status == "success":
            logger.info("  Scene %d: %s → %s", i + 1, status, r["output_path"])
        else:
            logger.error("  Scene %d: %s → %s", i + 1, status, r.get("error", ""))


if __name__ == "__main__":
    main()
