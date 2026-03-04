"""Synthesize panel — Step 6 of the pipeline.

Invokes the Voice Synthesizer to produce per-scene narration audio
with filler injection and SSML pacing, then displays the audio manifest.
"""

import json
import logging

import streamlit as st

from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline

logger = logging.getLogger("pipeline_ui")


def render_synthesize_panel() -> None:
    """Step 6: Synthesize narration audio for each scene."""
    pipeline = get_pipeline()

    st.subheader("Voice Synthesis")

    if pipeline.video_script is None:
        st.warning("No VideoScript available. Complete the Convert step first.")
        return

    vs = pipeline.video_script
    st.caption(
        f"Script: {vs.title} | {len(vs.scenes)} scenes | "
        f"{vs.total_word_count} words"
    )

    # Show existing manifest if already synthesized
    if pipeline.audio_manifest is not None:
        _render_manifest(pipeline.audio_manifest)
        st.info("Audio already synthesized. Re-run to regenerate.")

    if st.button("Synthesize Audio", key="synthesize_btn"):
        _run_synthesis(pipeline)

    # Navigation
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Review", key="synth_back"):
            go_to_step(PipelineStep.REVIEW, pipeline)
            st.rerun()
    with col2:
        can_proceed = pipeline.audio_manifest is not None
        if st.button(
            "Continue to Render →",
            disabled=not can_proceed,
            key="synth_advance",
        ):
            pipeline.max_completed_step = max(
                pipeline.max_completed_step, int(PipelineStep.SYNTHESIZE)
            )
            go_to_step(PipelineStep.RENDER, pipeline)
            st.rerun()


def _run_synthesis(pipeline) -> None:
    """Invoke VoiceSynthesizer and store the AudioManifest."""
    from voice_synthesizer.exceptions import AuthenticationError
    from voice_synthesizer.synthesizer import VoiceSynthesizer

    with st.spinner("Synthesizing narration…"):
        try:
            synth = VoiceSynthesizer()
            manifest = synth.synthesize(pipeline.video_script)

            pipeline.audio_manifest = manifest
            pipeline.max_completed_step = max(
                pipeline.max_completed_step, int(PipelineStep.SYNTHESIZE)
            )

            if manifest.total_scenes_failed == 0:
                st.success(
                    f"All {manifest.total_scenes_synthesized} scenes synthesized "
                    f"({manifest.total_duration_seconds:.1f}s total)"
                )
            else:
                st.warning(
                    f"{manifest.total_scenes_synthesized} OK, "
                    f"{manifest.total_scenes_failed} failed"
                )

            _render_manifest(manifest)

        except AuthenticationError as exc:
            logger.error("[Synthesize] AuthenticationError: %s", exc)
            st.error(f"⚙️ Configuration error: {exc}")
            st.info(
                "Check your TTS configuration in `.env`. "
                "For Fish Audio (default), set `FISH_API_KEY`. "
                "For ElevenLabs, set `ELEVENLABS_API_KEY`."
            )
        except Exception as exc:
            logger.error("[Synthesize] Unexpected error: %s", exc)
            st.error(f"Synthesis failed: {exc}")
            st.info("You can retry the synthesis.")


def _render_manifest(manifest) -> None:
    """Display the AudioManifest summary and per-scene details."""
    cols = st.columns(4)
    cols[0].metric("Scenes OK", str(manifest.total_scenes_synthesized))
    cols[1].metric("Scenes Failed", str(manifest.total_scenes_failed))
    cols[2].metric("Total Duration", f"{manifest.total_duration_seconds:.1f}s")
    cols[3].metric("Characters", str(manifest.total_characters_processed))

    for entry in manifest.entries:
        status = "✅" if entry.file_path else "❌"
        label = f"{status} Scene {entry.scene_number}"
        with st.expander(label):
            if entry.file_path:
                st.caption(f"Duration: {entry.duration_seconds:.1f}s | {entry.char_count} chars")
                st.code(entry.file_path, language="text")
                # Audio playback
                try:
                    st.audio(entry.file_path)
                except Exception:
                    st.caption("Audio preview unavailable")
            else:
                st.error(f"Error: {entry.error}")

    # Download manifest JSON
    manifest_json = json.dumps(manifest.to_dict(), indent=2)
    st.download_button(
        "Download Audio Manifest",
        manifest_json,
        file_name="audio_manifest.json",
        mime="application/json",
        key="download_manifest",
    )
