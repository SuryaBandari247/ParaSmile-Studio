#!/usr/bin/env python3
"""
End-to-end pipeline runner for Calm Capitalist.

Chains: Research Agent → Script Converter → Voice Synthesizer → Asset Orchestrator
Produces a final composed MP4 video from trending topic research.

Usage:
    python run_pipeline.py                    # Full interactive pipeline
    python run_pipeline.py --skip-research    # Use a raw script file instead
    python run_pipeline.py --script FILE      # Provide raw script directly
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Colour helpers (ANSI) ──────────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _banner(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}\n")


def _step(msg: str) -> None:
    print(f"{GREEN}▶ {msg}{RESET}")


def _warn(msg: str) -> None:
    print(f"{YELLOW}⚠ {msg}{RESET}")


def _error(msg: str) -> None:
    print(f"{RED}✖ {msg}{RESET}")


def _info(msg: str) -> None:
    print(f"  {msg}")


# ── Pre-flight checks ─────────────────────────────────────────────────────
def preflight() -> bool:
    """Verify all required API keys and tools are available."""
    ok = True
    for key in ("YOUTUBE_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY"):
        val = os.getenv(key, "")
        if not val or val.startswith("your_"):
            _error(f"Missing environment variable: {key}")
            ok = False
        else:
            _step(f"{key} ✓")

    import shutil

    if shutil.which("ffmpeg") is None:
        _error("FFmpeg not found on PATH")
        ok = False
    else:
        _step("FFmpeg ✓")

    try:
        import manim  # noqa: F401
        _step("Manim ✓")
    except ImportError:
        _error("Manim not installed (pip install manim)")
        ok = False

    return ok


# ── Stage 1: Research ──────────────────────────────────────────────────────
def stage_research() -> str:
    """Run multi-source research and pitch selection. Returns selected pitch text."""
    from research_agent.agent import ResearchAgent

    _banner("Stage 1 / 4 — Research Agent")
    agent = ResearchAgent()

    _step("Fetching trending topics from 5 sources...")
    topics = agent.get_trending_topics_multi_source()
    _info(f"Found {len(topics)} unified topics")

    if not topics:
        _error("No trending topics found. Try again later.")
        sys.exit(1)

    _step("Generating story pitches via GPT-4o-mini...")
    pitch = agent.generate_and_select_pitch(topics)

    _info(f"Selected: {pitch.title}")
    _info(f"Hook: {pitch.hook}")

    # Build a raw script prompt from the pitch
    raw_script = _pitch_to_raw_script(pitch)
    return raw_script


def _pitch_to_raw_script(pitch) -> str:
    """Convert a StoryPitch into a raw script string for the converter."""
    sources_text = ""
    for st in pitch.source_trends[:3]:
        sources_text += f"- Source: {st.source_name} ({st.source_url})\n"

    raw = f"""Title: {pitch.title}

Hook: {pitch.hook}

Category: {pitch.category}
Context: {pitch.context_type}
{f"Data note: {pitch.data_note}" if pitch.data_note else ""}

Sources:
{sources_text}
Please create a 5-8 scene educational video script about this topic.
Each scene should have clear narration and a visual instruction (bar_chart, line_chart, pie_chart, code_snippet, or text_overlay).
Include real data points and statistics where possible.
Keep the tone informative but engaging — like a documentary narrator.
"""
    return raw


# ── Stage 2: Script Conversion ────────────────────────────────────────────
def stage_convert(raw_script: str):
    """Convert raw script to structured VideoScript."""
    from script_generator.converter import ScriptConverter

    _banner("Stage 2 / 4 — Script Converter")
    _step("Converting raw script to structured VideoScript via GPT-4o-mini...")

    converter = ScriptConverter()
    video_script = converter.convert(raw_script)

    _info(f"Title: {video_script.title}")
    _info(f"Scenes: {len(video_script.scenes)}")
    _info(f"Total words: {video_script.total_word_count}")

    # Save script JSON for debugging
    from script_generator.serializer import ScriptSerializer
    serializer = ScriptSerializer()
    script_json = serializer.serialize(video_script)
    os.makedirs("output", exist_ok=True)
    with open("output/video_script.json", "w") as f:
        f.write(script_json)
    _info("Saved structured script → output/video_script.json")

    return video_script


# ── Stage 3: Voice Synthesis ──────────────────────────────────────────────
def stage_voice(video_script):
    """Synthesize narration audio for each scene."""
    from voice_synthesizer.synthesizer import VoiceSynthesizer

    _banner("Stage 3 / 4 — Voice Synthesizer")
    _step("Synthesizing narration with filler injection...")

    synth = VoiceSynthesizer()
    manifest = synth.synthesize(video_script)

    _info(f"Scenes synthesized: {manifest.total_scenes_synthesized}")
    _info(f"Scenes failed: {manifest.total_scenes_failed}")
    _info(f"Total duration: {manifest.total_duration_seconds:.1f}s")
    _info(f"Characters processed: {manifest.total_characters_processed}")

    # Save manifest
    os.makedirs("output", exist_ok=True)
    with open("output/audio_manifest.json", "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)
    _info("Saved audio manifest → output/audio_manifest.json")

    if manifest.total_scenes_failed > 0:
        for entry in manifest.entries:
            if entry.error:
                _warn(f"Scene {entry.scene_number} failed: {entry.error}")

    return manifest


# ── Stage 4: Asset Orchestration ──────────────────────────────────────────
def stage_assets(video_script, audio_manifest):
    """Render visuals and compose final video segments."""
    from asset_orchestrator.orchestrator import AssetOrchestrator

    _banner("Stage 4 / 4 — Asset Orchestrator")
    _step("Rendering scenes and composing with audio...")

    orchestrator = AssetOrchestrator()

    instructions = []
    audio_paths = []
    narration_texts = []

    for scene in sorted(video_script.scenes, key=lambda s: s.scene_number):
        instructions.append(scene.visual_instruction)
        audio_path = audio_manifest.get_audio_path(scene.scene_number)
        audio_paths.append(audio_path)
        narration_texts.append(getattr(scene, "narration_text", "") or "")

    result = orchestrator.process_batch(instructions, audio_paths, narration_texts)

    _info(f"Total: {result.total}")
    _info(f"Succeeded: {result.succeeded}")
    _info(f"Failed: {result.failed}")

    # Collect successful output paths
    composed_paths = []
    for i, r in enumerate(result.results):
        if r["status"] == "success":
            composed_paths.append(r["output_path"])
            _info(f"Scene {i + 1}: {r['output_path']}")
        else:
            _warn(f"Scene {i + 1} failed: {r.get('error', 'unknown')}")

    if result.failed > 0:
        _warn(f"{result.failed} scene(s) failed to render")

    # Concatenate all composed scenes into final video
    if len(composed_paths) > 1:
        final_path = _concatenate_scenes(composed_paths)
    elif composed_paths:
        final_path = composed_paths[0]
    else:
        _error("No scenes rendered successfully. Cannot produce final video.")
        return None

    return final_path


def _concatenate_scenes(scene_paths: list[str]) -> str:
    """Use FFmpeg to concatenate multiple scene videos into one final MP4."""
    import subprocess
    import tempfile

    _step("Concatenating scenes into final video...")

    os.makedirs("output/final", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = f"output/final/video_{timestamp}.mp4"

    # Write concat file list
    concat_file = os.path.join("output", "concat_list.txt")
    with open(concat_file, "w") as f:
        for p in scene_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        final_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        _step(f"Final video: {os.path.abspath(final_path)}")
    except subprocess.CalledProcessError as e:
        _error(f"Concatenation failed: {e.stderr}")
        # Fall back to returning the first scene
        _warn("Returning first scene as output")
        return scene_paths[0]

    return os.path.abspath(final_path)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Calm Capitalist — End-to-End Pipeline"
    )
    parser.add_argument(
        "--skip-research", action="store_true",
        help="Skip research stage; provide raw script via --script",
    )
    parser.add_argument(
        "--script", type=str, default=None,
        help="Path to a raw script text file (used with --skip-research)",
    )
    args = parser.parse_args()

    _banner("Calm Capitalist")
    _step("Running pre-flight checks...")

    if not preflight():
        _error("Pre-flight checks failed. Fix the issues above and retry.")
        sys.exit(1)

    _step("All checks passed. Starting pipeline...\n")
    t0 = time.time()

    # Stage 1: Research (or load script)
    if args.skip_research:
        if not args.script:
            _error("--skip-research requires --script <file>")
            sys.exit(1)
        if not os.path.isfile(args.script):
            _error(f"Script file not found: {args.script}")
            sys.exit(1)
        with open(args.script) as f:
            raw_script = f.read()
        _step(f"Loaded raw script from {args.script} ({len(raw_script)} chars)")
    else:
        raw_script = stage_research()

    # Save raw script for reference
    os.makedirs("output", exist_ok=True)
    with open("output/raw_script.txt", "w") as f:
        f.write(raw_script)

    # Stage 2: Convert
    video_script = stage_convert(raw_script)

    # Stage 3: Voice
    audio_manifest = stage_voice(video_script)

    # Stage 4: Assets + Composition
    final_path = stage_assets(video_script, audio_manifest)

    elapsed = time.time() - t0

    _banner("Pipeline Complete")
    if final_path:
        _step(f"Final video: {final_path}")
    _info(f"Total time: {elapsed:.1f}s")
    _info(f"Artifacts saved in output/")


if __name__ == "__main__":
    main()
