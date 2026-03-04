"""Render panel — Step 7 of the pipeline.

Invokes the Asset Orchestrator to render Manim scenes from visual
instructions, compose them with audio, and concatenate into a final MP4.
"""

import logging
import os
import subprocess
from datetime import datetime

import streamlit as st

from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline

logger = logging.getLogger("pipeline_ui")


def render_render_panel() -> None:
    """Step 7: Render visuals and compose final video."""
    pipeline = get_pipeline()

    st.subheader("Render & Compose")

    if pipeline.video_script is None:
        st.warning("No VideoScript available. Complete earlier steps first.")
        return
    if pipeline.audio_manifest is None:
        st.warning("No audio manifest. Complete the Synthesize step first.")
        return

    vs = pipeline.video_script
    manifest = pipeline.audio_manifest

    st.caption(
        f"Script: {vs.title} | {len(vs.scenes)} scenes | "
        f"Audio: {manifest.total_scenes_synthesized} tracks "
        f"({manifest.total_duration_seconds:.1f}s)"
    )

    # Show existing result
    if pipeline.render_result is not None:
        _render_result_summary(pipeline.render_result, pipeline.final_video_path)

    if st.button("Render Video", key="render_btn"):
        _run_render(pipeline)

    # Back navigation
    if st.button("← Back to Synthesize", key="render_back"):
        go_to_step(PipelineStep.SYNTHESIZE, pipeline)
        st.rerun()


def _run_render(pipeline) -> None:
    """Invoke AssetOrchestrator batch processing and optional concatenation."""
    from asset_orchestrator.orchestrator import AssetOrchestrator

    vs = pipeline.video_script
    manifest = pipeline.audio_manifest

    instructions = []
    audio_paths = []

    for scene in sorted(vs.scenes, key=lambda s: s.scene_number):
        instructions.append(scene.visual_instruction)
        audio_path = manifest.get_audio_path(scene.scene_number)
        audio_paths.append(audio_path)

    progress = st.progress(0, text="Rendering scenes…")

    try:
        orchestrator = AssetOrchestrator()
        total = len(instructions)
        results = []
        succeeded = 0
        failed = 0

        for i, instruction in enumerate(instructions):
            progress.progress(
                (i + 1) / total,
                text=f"Rendering scene {i + 1}/{total}…",
            )
            audio_path = audio_paths[i] if i < len(audio_paths) else None
            result = orchestrator.process_instruction(instruction, audio_path)
            results.append(result)

            if result["status"] == "success":
                succeeded += 1
            else:
                failed += 1

        progress.progress(1.0, text="Rendering complete")

        # Store batch result
        from asset_orchestrator.config import BatchResult
        batch = BatchResult(
            total=total, succeeded=succeeded, failed=failed, results=results
        )
        pipeline.render_result = batch

        # Concatenate successful scenes
        composed_paths = [
            r["output_path"] for r in results if r["status"] == "success"
        ]

        final_path = None
        if len(composed_paths) > 1:
            final_path = _concatenate(composed_paths)
        elif composed_paths:
            final_path = composed_paths[0]

        pipeline.final_video_path = final_path
        pipeline.max_completed_step = max(
            pipeline.max_completed_step, int(PipelineStep.RENDER)
        )

        if failed == 0:
            st.success(f"All {succeeded} scenes rendered successfully")
        else:
            st.warning(f"{succeeded} OK, {failed} failed")

        _render_result_summary(batch, final_path)

    except Exception as exc:
        logger.error("[Render] Unexpected error: %s", exc)
        st.error(f"Rendering failed: {exc}")
        st.info("Check that FFmpeg and Manim are installed correctly.")


def _concatenate(scene_paths: list[str]) -> str | None:
    """Concatenate scene videos into a single final MP4."""
    os.makedirs("output/final", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = f"output/final/video_{timestamp}.mp4"

    concat_file = os.path.join("output", "concat_list.txt")
    with open(concat_file, "w") as f:
        for p in scene_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", final_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return os.path.abspath(final_path)
    except subprocess.CalledProcessError as exc:
        logger.error("[Render] Concatenation failed: %s", exc.stderr)
        return scene_paths[0] if scene_paths else None


def _render_result_summary(batch, final_path: str | None) -> None:
    """Display render results and final video."""
    cols = st.columns(3)
    cols[0].metric("Total Scenes", str(batch.total))
    cols[1].metric("Succeeded", str(batch.succeeded))
    cols[2].metric("Failed", str(batch.failed))

    # Per-scene results
    for i, r in enumerate(batch.results):
        status = "✅" if r["status"] == "success" else "❌"
        with st.expander(f"{status} Scene {i + 1}"):
            if r["status"] == "success":
                st.code(r["output_path"], language="text")
                try:
                    st.video(r["output_path"])
                except Exception:
                    st.caption("Video preview unavailable")
            else:
                st.error(r.get("error", "Unknown error"))

    # Final video
    if final_path and os.path.isfile(final_path):
        st.markdown("---")
        st.markdown("**Final Video**")
        try:
            st.video(final_path)
        except Exception:
            st.caption("Video preview unavailable")

        with open(final_path, "rb") as f:
            st.download_button(
                "Download Final Video",
                f.read(),
                file_name=os.path.basename(final_path),
                mime="video/mp4",
                key="download_final_video",
            )

        st.code(final_path, language="text")
