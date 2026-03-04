"""Review panel — Step 5 of the pipeline.

Displays the structured VideoScript for review, including scene blocks,
metadata, and provides JSON download and back-navigation options.
"""

import streamlit as st

from pipeline_ui.navigation import PipelineStep, go_to_step
from pipeline_ui.session_state import get_pipeline
from script_generator.serializer import ScriptSerializer


def render_review_panel() -> None:
    """Step 5: Display the VideoScript for review with download option."""
    pipeline = get_pipeline()
    vs = pipeline.video_script

    if vs is None:
        st.warning("No VideoScript available. Please complete the Convert step first.")
        return

    # Header: title, word count, timestamp
    st.subheader(vs.title)
    st.caption(
        f"Words: {vs.total_word_count} | Generated: {vs.generated_at.isoformat()}"
    )

    # Scene blocks
    for scene in vs.scenes:
        with st.expander(f"Scene {scene.scene_number}", expanded=True):
            st.write(scene.narration_text)
            vi = scene.visual_instruction
            st.code(
                f"Type: {vi.get('type')} | Title: {vi.get('title')}",
            )
            st.json(vi.get("data", {}))

    # Serialize for download and raw view
    serializer = ScriptSerializer()
    json_str = serializer.serialize(vs)

    # Download button
    st.download_button(
        "Download VideoScript JSON",
        json_str,
        file_name="video_script.json",
        mime="application/json",
    )

    # Raw JSON collapsible
    with st.expander("Raw JSON"):
        st.code(json_str, language="json")

    # Back to Script button
    if st.button("Back to Script"):
        go_to_step(PipelineStep.SCRIPT_INPUT, pipeline)
        st.rerun()

    # Advance to Synthesize
    if st.button("Continue to Synthesize →", key="review_advance"):
        pipeline.max_completed_step = max(
            pipeline.max_completed_step, int(PipelineStep.REVIEW)
        )
        go_to_step(PipelineStep.SYNTHESIZE, pipeline)
        st.rerun()
